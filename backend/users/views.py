from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.mixins import RetrieveModelMixin
from django.db.models import Count, Q

from .models import User
from .serializers import (
    UserRegistrationSerializer, 
    UserProfileSerializer, 
    UserUpdateSerializer, 
    PublicUserSerializer,
    ChangePasswordSerializer
)
from .services import register_user, update_profile

class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(**serializer.validated_data)
        
        return Response(
            UserRegistrationSerializer(user).data,
            status=status.HTTP_201_CREATED
        )

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = User.objects.annotate(
            settlement_count=Count('sent_settlements', filter=Q(sent_settlements__status='CONFIRMED')) + 
                             Count('received_settlements', filter=Q(received_settlements__status='CONFIRMED'))
        ).get(id=request.user.id)
        
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = update_profile(request.user, serializer.validated_data)
        
        # Return updated profile data (need to re-fetch to get annotations if needed, but here we can just serialize without annotations or fetch again)
        updated_user = User.objects.annotate(
            settlement_count=Count('sent_settlements', filter=Q(sent_settlements__status='CONFIRMED')) + 
                             Count('received_settlements', filter=Q(received_settlements__status='CONFIRMED'))
        ).get(id=user.id)
        
        return Response(UserProfileSerializer(updated_user).data)

class UserProfileViewSet(RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PublicUserSerializer

    def get_queryset(self):
        return User.objects.filter(is_active=True).annotate(
            settlement_count=Count('sent_settlements', filter=Q(sent_settlements__status='CONFIRMED')) + 
                             Count('received_settlements', filter=Q(received_settlements__status='CONFIRMED'))
        )

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)