from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GroupViewSet

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')

# All routes generated:
#   GET/POST       /api/v1/groups/
#   GET/PATCH/DEL  /api/v1/groups/{id}/
#   POST           /api/v1/groups/{id}/add-member/
#   POST           /api/v1/groups/{id}/remove-member/
#   GET            /api/v1/groups/{id}/invite-code/
#   POST           /api/v1/groups/{id}/regenerate-invite/
#   POST           /api/v1/groups/join/

urlpatterns = [path('', include(router.urls))]