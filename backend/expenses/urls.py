from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet

# Router handles standard URL patterns for the ViewSet
router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')

urlpatterns = [
    path('', include(router.urls)),
]