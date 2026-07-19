"""
groups/serializers.py
─────────────────────
Serializers for the groups domain.

Three context-specific user representations:
  SlimUserSerializer   — safe embed for group contexts (no PII)
  GroupSerializer      — member view (no invite_code)
  GroupAdminSerializer — admin view (adds invite_code)

BudgetSerializer lives in analytics/serializers.py — Budget is an analytics
concern, not a group concern.
"""
from rest_framework import serializers
from .models import Group, GroupMembership


class SlimUserSerializer(serializers.Serializer):
    """
    Safe, minimal user representation for embedding in group contexts.
    Exposes ONLY what other group members need to see.
    Intentionally excludes: email, upi_id, currency_preference — PII.
    """
    id                = serializers.IntegerField(read_only=True)
    username          = serializers.CharField(read_only=True)
    avatar_url        = serializers.URLField(read_only=True, allow_null=True)
    reliability_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)


class GroupMembershipSerializer(serializers.ModelSerializer):
    """Surfaces role and join date from the through model with slim user data."""
    user = SlimUserSerializer(read_only=True)

    class Meta:
        model  = GroupMembership
        fields = ['user', 'role', 'joined_at']


class GroupSerializer(serializers.ModelSerializer):
    """
    Standard group representation for members.
    invite_code is intentionally absent — members cannot see or share it.
    Use GroupAdminSerializer when the requesting user is the group admin.
    """
    memberships    = GroupMembershipSerializer(
        source='groupmembership_set', many=True, read_only=True
    )
    admin_username = serializers.ReadOnlyField(source='admin.username')
    member_count   = serializers.SerializerMethodField()

    class Meta:
        model  = Group
        fields = [
            'id', 'name', 'description', 'emoji', 'currency',
            'admin', 'admin_username',
            'memberships', 'member_count',
            'created_at',
            # invite_code intentionally absent from this serializer
        ]
        read_only_fields = ['admin', 'admin_username', 'member_count', 'created_at']

    def get_member_count(self, obj) -> int:
        return obj.members.count()


class GroupAdminSerializer(GroupSerializer):
    """
    Extended serializer for the group admin only.
    Adds invite_code — only the admin should see and share this.
    Returned by GroupViewSet.get_serializer_class() when requester == admin.
    """
    class Meta(GroupSerializer.Meta):
        fields = GroupSerializer.Meta.fields + ['invite_code']

