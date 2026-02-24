from django.shortcuts import render
from rest_framework import generics, viewsets, status
from rest_framework.decorators import action 
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import UserSerializer
from .models import ReliabilityHistory 

class RegisterView(generics.CreateAPIView):
    """
    Endpoint for new user registration.
    Accessible to everyone to allow onboarding.
    """
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User registered successfully",
                "user": UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# FIX: Switch to GenericViewSet to support both Profile and Score History
class UserProfileViewSet(viewsets.GenericViewSet):
    """
    Combined ViewSet to handle Profile retrieval/updates 
    and the Reliability Score History.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    # GET /api/users/profile/me/
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def manage_profile(self, request):
        user = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        
        # Handle Updates (PUT/PATCH)
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET /api/users/profile/score-history/
    @action(detail=False, methods=['get'], url_path='score-history')
    def get_score_history(self, request):
        history = ReliabilityHistory.objects.filter(user=request.user).order_by('timestamp')
        data = [{"score": float(h.score), "date": h.timestamp.strftime("%Y-%m-%d")} for h in history]
        return Response(data)