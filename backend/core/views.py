from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.conf import settings
from rest_framework.response import Response

class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            refresh_token = response.data.get('refresh')
            if refresh_token:
                # Remove refresh token from response body
                del response.data['refresh']
                # Set refresh token in HttpOnly cookie
                response.set_cookie(
                    key='refresh_token',
                    value=refresh_token,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                    max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
                )
        return response

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # The refresh token might be in the cookie
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            # Inject it into request data so TokenRefreshView can use it
            if 'refresh' not in request.data:
                request.data._mutable = True if hasattr(request.data, '_mutable') else request.data
                try:
                    request.data['refresh'] = refresh_token
                except TypeError:
                    # If request.data is immutable and doesn't have _mutable (like QueryDict)
                    # We might need to copy it
                    new_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
                    new_data['refresh'] = refresh_token
                    request._full_data = new_data
        
        try:
            response = super().post(request, *args, **kwargs)
        except (InvalidToken, TokenError) as e:
            # Handle token errors
            return Response({"error": "Invalid or expired token"}, status=401)
        
        if response.status_code == 200:
            new_refresh_token = response.data.get('refresh')
            if new_refresh_token:
                del response.data['refresh']
                response.set_cookie(
                    key='refresh_token',
                    value=new_refresh_token,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                    max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
                )
        return response


class CookieTokenBlacklistView(TokenBlacklistView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            if 'refresh' not in request.data:
                request.data._mutable = True if hasattr(request.data, '_mutable') else request.data
                try:
                    request.data['refresh'] = refresh_token
                except TypeError:
                    new_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
                    new_data['refresh'] = refresh_token
                    request._full_data = new_data

        try:
            response = super().post(request, *args, **kwargs)
        except (InvalidToken, TokenError):
            response = Response({"detail": "Token already invalid or expired, logged out successfully."}, status=200)

        response.delete_cookie('refresh_token')
        return response


class CookieLogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tokens = OutstandingToken.objects.filter(user=request.user)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
        
        response = Response({"detail": "Successfully logged out from all devices."}, status=200)
        response.delete_cookie('refresh_token')
        return response
