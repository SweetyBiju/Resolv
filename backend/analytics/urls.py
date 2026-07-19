from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BudgetViewSet, AnalyticsView

router = DefaultRouter()
router.register(r'budgets', BudgetViewSet, basename='budget')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/trends/', AnalyticsView.as_view({'get': 'get_trends'})),
    path('analytics/categories/', AnalyticsView.as_view({'get': 'get_categories'})),
    path('analytics/budget/', AnalyticsView.as_view({'get': 'get_budget'})),
    path('analytics/insights/', AnalyticsView.as_view({'get': 'get_insights'})),
    path('analytics/export/', AnalyticsView.as_view({'get': 'export'})),
]
