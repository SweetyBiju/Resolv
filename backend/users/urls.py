from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import RegisterView, UserMeView, UserProfileViewSet, ChangePasswordView

router = DefaultRouter()
router.register(r'users/profile', UserProfileViewSet, basename='profile')

urlpatterns = [
    path('users/register/', RegisterView.as_view(), name='register'),
    path('users/me/', UserMeView.as_view(), name='user-me'),
    path('users/change-password/', ChangePasswordView.as_view(), name='change-password'),
] + router.urls