"""
activity/views.py
─────────────────
Read-only API for the audit trail.
Users see only their own logs. Admins can filter by group via ?group_id=.
No create/update/delete — logs are written exclusively by the service layer.
"""
import logging
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated

from .models import ActivityLog
from .serializers import ActivityLogSerializer

logger = logging.getLogger('resolv.activity')


from core.pagination import ActivityPagination
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError

class ActivityLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class   = ActivityLogSerializer
    pagination_class   = ActivityPagination

    def get_queryset(self):
        group_id = self.request.query_params.get('group_id')

        # Shared filter params
        action_filter = self.request.query_params.get('action')
        date_after    = self.request.query_params.get('date_after')
        date_before   = self.request.query_params.get('date_before')

        if group_id:
            # BUG 5 FIX: validate that group_id is a digit before int() cast,
            # otherwise int('abc') raises ValueError and crashes with a 500.
            if not str(group_id).isdigit():
                raise ValidationError("group_id must be a positive integer.")

            # Security check: requesting user must be a member of the group
            from groups.models import Group
            group = Group.objects.filter(id=group_id).first()
            if not group or not group.members.filter(id=self.request.user.id).exists():
                raise PermissionDenied("You do not have access to this group's activity.")
            # Return all activity for the group (any actor), not just the current user
            qs = (
                ActivityLog.objects
                .filter(details__group_id=int(group_id))
                .select_related('user')
                .order_by('-timestamp')
            )
        else:
            # No group filter — return only the requesting user's own logs
            qs = (
                ActivityLog.objects
                .filter(user=self.request.user)
                .select_related('user')
                .order_by('-timestamp')
            )

        # Apply optional filters
        if action_filter:
            qs = qs.filter(action=action_filter)
        if date_after:
            qs = qs.filter(timestamp__date__gte=date_after)
        if date_before:
            qs = qs.filter(timestamp__date__lte=date_before)

        return qs