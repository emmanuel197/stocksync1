from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from .models import Order, OrderItem, Product, Inventory, InventoryMovement
from decimal import Decimal

def get_date_range_from_period(period_str):
    """
    Calculates start_date and end_date based on a period string.
    Supported periods: 'today', 'this_week', 'this_month', 'last_7_days', 'last_30_days'.
    Returns (start_date, end_date).
    """
    now = timezone.now()
    start_date, end_date = None, now

    if period_str == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'this_week':
        start_date = (now - timezone.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'last_7_days':
        start_date = (now - timezone.timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'last_30_days':
        start_date = (now - timezone.timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    # Add more custom periods as needed

    return start_date, end_date


def get_sales_overview(organization, start_date=None, end_date=None):
    """
    Calculates a comprehensive sales overview for a given organization and date range.
    """
    if start_date is None and end_date is None: # Default to this month if no dates provided
        end_date = timezone.now()
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    orders_qs = Order.objects.filter(
        organization=organization,
        status__in=['delivered', 'completed'], # Consider which statuses count as a sale
        order_date__gte=start_date,
        order_date__lte=end_date
    )

    summary = orders_qs.aggregate(
        total_revenue=Sum('total_amount'),
        total_orders=Count('id')
    )

    total_revenue = summary['total_revenue'] or Decimal('0.00')
    total_orders = summary['total_orders'] or 0

    order_items_qs = OrderItem.objects.filter(
        order__in=orders_qs
    ).select_related('product')

    total_items_sold = order_items_qs.aggregate(Sum('quantity'))['quantity__sum'] or 0

    total_cogs = Decimal('0.00')
    for item in order_items_qs:
        if item.product and item.product.cost is not None:
            total_cogs += item.quantity * item.product.cost

    net_profit = total_revenue - total_cogs
    average_sale_value = total_revenue / total_orders if total_orders > 0 else Decimal('0.00')
    average_items_per_sale = total_items_sold / total_orders if total_orders > 0 else 0

    return {
        'start_date': start_date.isoformat() if start_date else None,
        'end_date': end_date.isoformat() if end_date else None,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_items_sold': total_items_sold,
        'average_sale_value': average_sale_value,
        'average_items_per_sale': average_items_per_sale,
        'total_cogs': total_cogs,
        'net_profit': net_profit,
    }

def get_sales_trend(organization, start_date, end_date, interval='day'):
    """
    Calculates sales trend data for a given organization, date range, and interval.
    Interval can be 'day', 'week', 'month'.
    """
    trunc_func = TruncDay
    if interval == 'week':
        trunc_func = TruncWeek
    elif interval == 'month':
        trunc_func = TruncMonth

    sales_data = Order.objects.filter(
        organization=organization,
        status__in=['delivered', 'completed'],
        order_date__gte=start_date,
        order_date__lte=end_date
    ).annotate(
        period=trunc_func('order_date')
    ).values('period').annotate(
        total_sales=Sum('total_amount')
    ).order_by('period')

    return [{'date': item['period'].isoformat(), 'sales': item['total_sales'] or 0} for item in sales_data]

def get_top_selling_products(organization, start_date, end_date, limit=5, by='revenue'):
    """
    Gets top selling products by revenue or units sold.
    """
    order_items_qs = OrderItem.objects.filter(
        order__organization=organization,
        order__status__in=['delivered', 'completed'],
        order__order_date__gte=start_date,
        order__order_date__lte=end_date
    ).select_related('product')

    if by == 'revenue':
        top_products = order_items_qs.values(
            'product__id', 'product__name'
        ).annotate(
            total_value=Sum(F('quantity') * F('unit_price')),
            units_sold=Sum('quantity')
        ).order_by('-total_value')[:limit]
        return [{'product_id': p['product__id'], 'product_name': p['product__name'], 'total_revenue': p['total_value'], 'units_sold': p['units_sold']} for p in top_products]
    elif by == 'units':
        top_products = order_items_qs.values(
            'product__id', 'product__name'
        ).annotate(
            units_sold=Sum('quantity'),
            total_value=Sum(F('quantity') * F('unit_price'))
        ).order_by('-units_sold')[:limit]
        return [{'product_id': p['product__id'], 'product_name': p['product__name'], 'units_sold': p['units_sold'], 'total_revenue': p['total_value']} for p in top_products]
    return []

def get_inventory_summary(organization):
    """
    Provides a summary of the current inventory.
    """
    inventory_items = Inventory.objects.filter(organization=organization).select_related('product')

    total_stock_units = inventory_items.aggregate(total=Sum('quantity'))['total'] or 0
    
    total_stock_value = Decimal('0.00')
    for item in inventory_items:
        if item.product and item.product.cost is not None:
            total_stock_value += item.quantity * item.product.cost
            
    low_stock_items_count = inventory_items.filter(quantity__lte=F('min_stock_level')).count()
    
    # For DOH (Days of Inventory on Hand), we need average daily COGS.
    # This is a simplified version. For more accuracy, use a longer period for COGS.
    last_30_days_start, last_30_days_end = get_date_range_from_period('last_30_days')
    if last_30_days_start:
        sales_info_30_days = get_sales_overview(organization, last_30_days_start, last_30_days_end)
        cogs_last_30_days = sales_info_30_days['total_cogs']
        avg_daily_cogs = cogs_last_30_days / 30 if cogs_last_30_days > 0 else Decimal('0.00')
        days_on_hand = total_stock_value / avg_daily_cogs if avg_daily_cogs > 0 else Decimal('0.00')
    else:
        days_on_hand = Decimal('0.00')


    return {
        'total_stock_units': total_stock_units,
        'total_stock_value': total_stock_value,
        'low_stock_items_count': low_stock_items_count,
        'approx_days_on_hand': days_on_hand
    }