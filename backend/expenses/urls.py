from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet, SettlementViewSet

# Router handles standard URL patterns for the ViewSet
router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'settlements', SettlementViewSet, basename='settlement') 

urlpatterns = [
    path('', include(router.urls)),
]