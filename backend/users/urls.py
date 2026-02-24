from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, UserProfileViewSet

# 1. Initialize the router
router = DefaultRouter()

# 2. Register your ViewSet with the router
router.register(r'profile', UserProfileViewSet, basename='profile')

urlpatterns = [
    # Keep standard views using path()
    path('register/', RegisterView.as_view(), name='register'),
    
    # 3. Include the router URLs
    path('', include(router.urls)),
]