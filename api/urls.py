from django.urls import path
from .views import *  # Ensure new analytics views are imported if using *
# Or explicitly import:
# from .views import (
#   AnalyticsDashboardView, SalesTrendAnalyticsView, TopSellingProductsAnalyticsView,
#   ... other views ...
# )

app_name = 'api'
urlpatterns = [
    path('products/', ProductAPIView.as_view()),
    path('create-order/', CreateOrUpdateOrderView.as_view()),
    path('cart-data/', CartDataView.as_view()),
    path('update-cart/', updateCartView.as_view()),
    path('process-order/', ProcessOrderView.as_view()),
    path('unauth-process-order/', UnAuthProcessOrderView.as_view()),
    path('search/', ProductSearchView.as_view()),
    path('products/filter/', FilteredProductListView.as_view()),
    path('onboarding/', OrganizationOnboardingView.as_view(), name='organization-onboarding'),
    path('organizations/activate/<uuid:token>/', OrganizationActivationView.as_view(), name='activate-organization'),
    path('relationships/', OrganizationRelationshipListView.as_view(), name='relationship-list'),
    path('relationships/request/', OrganizationRelationshipRequestView.as_view(), name='relationship-request'),
    path('relationships/<int:pk>/update/', OrganizationRelationshipUpdateView.as_view(), name='relationship-update'),
    path('potential-suppliers/', PotentialSupplierListView.as_view(), name='potential-supplier-list'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('inventory/', InventoryListView.as_view(), name='inventory-list'),
    path('inventory/<int:pk>/', InventoryDetailView.as_view(), name='inventory-detail'),
    path('inventory/create/', InventoryCreateView.as_view(), name='inventory-create'),
    path('inventory/<int:pk>/update/', InventoryUpdateView.as_view(), name='inventory-update'),
    path('inventory-movements/', InventoryMovementListView.as_view(), name='inventory-movement-list'),
    path('brands/', BrandListView.as_view(), name='brand-list-create'),
    path('brands/<int:pk>/', BrandDetailView.as_view(), name='brand-detail-update-delete'),
    path('categories/', CategoryListView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail-update-delete'),
    path('locations/', LocationListView.as_view(), name='location-list-create'),
    path('locations/<int:pk>/', LocationDetailView.as_view(), name='location-detail-update-delete'),

    # Analytics URLs
    path('analytics/dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('analytics/sales-trend/', SalesTrendAnalyticsView.as_view(), name='analytics-sales-trend'),
    path('analytics/top-products/', TopSellingProductsAnalyticsView.as_view(), name='analytics-top-products'),
    # Add more analytics URLs here as needed
]
