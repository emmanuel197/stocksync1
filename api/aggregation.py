from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from .models import Order, OrderItem, Product, Inventory, InventoryMovement
from decimal import Decimal
from django.db.models import OuterRef, Subquery # Import Subquery and OuterRef

def get_date_range_from_period(period_str):
    """
    Calculates start_date and end_date based on a period string.
    Supported periods: 'today', 'this_week', 'this_month', 'last_7_days', 'last_30_days'.
    Returns (start_date, end_date).
    """
    now = timezone.now()
    start_date, end_date = None, now # Initialize end_date to now

    if period_str == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'this_week':
        # Monday as the start of the week
        start_date = (now - timezone.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'last_7_days':
        start_date = (now - timezone.timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'last_30_days':
        start_date = (now - timezone.timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    # Add more custom periods as needed

    # Ensure start_date is timezone-aware if now is
    if timezone.is_aware(now) and start_date and timezone.is_naive(start_date):
         start_date = timezone.make_aware(start_date.replace(tzinfo=None), timezone.get_current_timezone())
    if timezone.is_aware(now) and end_date and timezone.is_naive(end_date):
         end_date = timezone.make_aware(end_date.replace(tzinfo=None), timezone.get_current_timezone())


    return start_date, end_date


def get_sales_overview(organization, start_date=None, end_date=None):
    """
    Calculates a comprehensive sales overview for a given organization (as a supplier)
    within a date range.
    """
    if start_date is None and end_date is None: # Default to this month if no dates provided
        end_date = timezone.now()
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if timezone.is_aware(end_date):
             start_date = timezone.make_aware(start_date.replace(tzinfo=None), timezone.get_current_timezone())


    # Filter OrderItems where the product belongs to the given organization
    # and the associated order is completed within the date range.
    order_items_qs = OrderItem.objects.filter(
        product__organization=organization, # Filter by the product's organization
        order__status__in=['delivered', 'completed'], # Consider which statuses count as a sale
        order__order_date__gte=start_date,
        order__order_date__lte=end_date
    ).select_related('product', 'order') # Select related for efficiency

    # Aggregate data from the filtered OrderItems
    summary = order_items_qs.aggregate(
        total_revenue=Sum(F('quantity') * F('unit_price'), output_field=DecimalField()),
        total_items_sold=Sum('quantity')
    )

    total_revenue = summary['total_revenue'] or Decimal('0.00')
    total_items_sold = summary['total_items_sold'] or 0

    # To get the count of unique orders, we can get the distinct order IDs from the filtered items
    total_orders = order_items_qs.values('order').distinct().count()

    total_cogs = Decimal('0.00')
    # Calculate COGS by iterating through the filtered order items
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
    Calculates sales trend data for a given organization (as a supplier),
    date range, and interval.
    Interval can be 'day', 'week', 'month'.
    """
    trunc_func = TruncDay
    if interval == 'week':
        trunc_func = TruncWeek
    elif interval == 'month':
        trunc_func = TruncMonth

    # Filter OrderItems where the product belongs to the given organization
    # and the associated order is completed within the date range.
    sales_data = OrderItem.objects.filter(
        product__organization=organization, # Filter by the product's organization
        order__status__in=['delivered', 'completed'],
        order__order_date__gte=start_date,
        order__order_date__lte=end_date
    ).annotate(
        # Truncate the order date of the associated order
        period=trunc_func('order__order_date')
    ).values('period').annotate(
        # Sum the revenue for items within each period
        total_sales=Sum(F('quantity') * F('unit_price'), output_field=DecimalField())
    ).order_by('period')

    # Ensure all periods in the range are included, even if sales are 0
    # This requires generating all dates/weeks/months in the range and merging.
    # For simplicity, we'll return the data as is. Frontend can handle filling gaps.

    return [{'date': item['period'].isoformat(), 'sales': item['total_sales'] or 0} for item in sales_data]

def get_top_selling_products(organization, start_date, end_date, limit=5, by='revenue'):
    """
    Gets top selling products for a given organization (as a supplier)
    by revenue or units sold within a date range.
    """
    # Filter OrderItems where the product belongs to the given organization
    # and the associated order is completed within the date range.
    order_items_qs = OrderItem.objects.filter(
        product__organization=organization, # Filter by the product's organization
        order__status__in=['delivered', 'completed'],
        order__order_date__gte=start_date,
        order__order_date__lte=end_date
    ).select_related('product')

    if by == 'revenue':
        top_products = order_items_qs.values(
            'product__id', 'product__name'
        ).annotate(
            total_value=Sum(F('quantity') * F('unit_price'), output_field=DecimalField()),
            units_sold=Sum('quantity')
        ).order_by('-total_value')[:limit]
        return [{'product_id': p['product__id'], 'product_name': p['product__name'], 'total_revenue': p['total_value'], 'units_sold': p['units_sold']} for p in top_products]
    elif by == 'units':
        top_products = order_items_qs.values(
            'product__id', 'product__name'
        ).annotate(
            units_sold=Sum('quantity'),
            total_value=Sum(F('quantity') * F('unit_price'), output_field=DecimalField())
        ).order_by('-units_sold')[:limit]
        return [{'product_id': p['product__id'], 'product_name': p['product__name'], 'units_sold': p['units_sold'], 'total_revenue': p['total_value']} for p in top_products]
    return []

def get_inventory_summary(organization):
    """
    Provides a summary of the current inventory for a given organization.
    This function already works from the perspective of the organization whose inventory it is.
    """
    inventory_items = Inventory.objects.filter(organization=organization).select_related('product')

    total_stock_units = inventory_items.aggregate(total=Sum('quantity'))['total'] or 0

    total_stock_value = Decimal('0.00')
    for item in inventory_items:
        if item.product and item.product.cost is not None:
            total_stock_value += item.quantity * item.product.cost

    low_stock_items_count = inventory_items.filter(quantity__lte=F('min_stock_level')).count()

    # For DOH (Days of Inventory on Hand), we need average daily COGS *for this organization's products*.
    # We can reuse the get_sales_overview function, which now calculates supplier-side COGS.
    last_30_days_start, last_30_days_end = get_date_range_from_period('last_30_days')
    if last_30_days_start:
        # Call the modified get_sales_overview to get COGS for this organization's sales
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