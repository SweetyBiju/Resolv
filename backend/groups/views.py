from django.shortcuts import render

# Create your views here.
# backend/groups/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Group
from .serializers import GroupSerializer 

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    def perform_create(self, serializer):
        # Automatically set the creator as the Admin
        group = serializer.save(admin=self.request.user)
        # Add the admin as the first member automatically
        group.members.add(self.request.user)

    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        """
        API to add a member to a group.
        Expects: {"user_id": <id>}
        """
        group = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            group.members.add(user_id)
            return Response({'status': 'member added'}, status=status.HTTP_200_OK)
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)