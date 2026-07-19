"""
activity/serializers.py
───────────────────────
Read-only serializer for ActivityLog.
ActivityLog is never written via API — only via the service layer.
"""
from rest_framework import serializers
from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    # Show username instead of raw FK integer
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = ActivityLog
        fields = ['id', 'user', 'action', 'timestamp', 'details']
        # Entire serializer is read-only — logs are never mutated via API
        read_only_fields = fields