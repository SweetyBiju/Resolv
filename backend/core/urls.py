from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from core.views import (
    CookieTokenObtainPairView, 
    CookieTokenRefreshView, 
    CookieTokenBlacklistView, 
    CookieLogoutAllView
)
from rest_framework.throttling import AnonRateThrottle
from drf_spectacular.views import (   # API docs
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


# ── Custom throttle for login endpoint ───────────────────────────────────────
class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'  # Defined in settings: 'login': '5/minute'


# ── Health check — no auth, no DB, instant response ──────────────────────────
def health_check(request):            
    return JsonResponse({'status': 'ok'})


# ── Versioned API URL block ───────────────────────────────────────────────────
v1_patterns = [
    # Auth
    path('auth/login/',   CookieTokenObtainPairView.as_view(
        throttle_classes=[LoginRateThrottle]  #  5/minute on login
    ), name='token_obtain_pair'),
    path('auth/refresh/', CookieTokenRefreshView.as_view(),   name='token_refresh'),
    path('auth/logout/',  CookieTokenBlacklistView.as_view(),  name='token_blacklist'),
    path('auth/logout-all/', CookieLogoutAllView.as_view(), name='logout_all'),

    # App URLs 
    path('', include('users.urls')),
    path('', include('expenses.urls')),
    path('', include('groups.urls')),
    path('', include('activity.urls')),
    path('', include('analytics.urls')),


    # API schema and docs
    path('schema/',  SpectacularAPIView.as_view(),        name='schema'),
    path('docs/',    SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/',   SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),
]

urlpatterns = [
    path('admin/',    admin.site.urls),
    path('health/',   health_check, name='health'),      
    path('api/v1/',   include((v1_patterns, 'v1'))),     
]