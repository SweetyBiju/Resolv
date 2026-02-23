from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .serializers import UserSerializer

class RegisterView(generics.CreateAPIView):
    """
    Endpoint for new user registration.
    Accessible to everyone to allow onboarding.
    """
    serializer_class = UserSerializer
    permission_classes = [AllowAny] # Override global IsAuthenticated setting

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User registered successfully",
                "user": UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint to retrieve or update the authenticated user's profile.
    Uses JWT for identification.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated] # Only logged-in users

    def get_object(self):
        # Returns the user associated with the JWT token
        return self.request.user