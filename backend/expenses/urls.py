"""
expenses/urls.py
────────────────
Registers ExpenseViewSet and SettlementViewSet with the default router.
Mount in core/urls.py under api/v1/:
  path('api/v1/', include('expenses.urls'))
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExpenseViewSet, SettlementViewSet

router = DefaultRouter()
router.register(r'expenses',    ExpenseViewSet,    basename='expense')
router.register(r'settlements', SettlementViewSet, basename='settlement')

urlpatterns = [path('', include(router.urls))]