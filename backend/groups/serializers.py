import uuid
from rest_framework import serializers
from .models import Group
from users.serializers import UserSerializer # To show member details

class GroupSerializer(serializers.ModelSerializer):
    """
    Handles Group data and auto-generates unique invite codes.
    """
    # Show member details using our existing UserSerializer
    members = UserSerializer(many=True, read_only=True)
    admin_username = serializers.ReadOnlyField(source='admin.username')

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'invite_code', 
            'admin', 'admin_username', 'members', 'created_at'
        ]
        # Admin is set in the view, invite_code is auto-generated
        read_only_fields = ['admin', 'invite_code']

   