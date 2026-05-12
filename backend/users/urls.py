from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, UserProfileViewSet,UserMeView

# 1. Initialize the router
router = DefaultRouter()

# 2. Register ViewSet with the router
router.register(r'profile', UserProfileViewSet, basename='profile')

urlpatterns = [
    
path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserMeView.as_view(), name='user_me'), 
    
    # Other user profiles routed via the ViewSet
    path('', include(router.urls)),
]