"""
activity/urls.py
────────────────
Registered under /api/v1/activity/ in core/urls.py.
Read-only router — no create/update/delete routes exposed.
"""
from rest_framework.routers import DefaultRouter
from .views import ActivityLogViewSet

router = DefaultRouter()
router.register(r'activity', ActivityLogViewSet, basename='activity')

urlpatterns = router.urls