"""
groups/permissions.py
─────────────────────
Two permission classes for the groups domain.

Critical rule: has_permission() AND has_object_permission() must BOTH be
implemented on every custom class. DRF only calls has_object_permission()
after has_permission() returns True. If has_permission() is absent, list and
create endpoints (which never call has_object_permission) have no auth guard.

Why .filter().exists() instead of `user in queryset`:
  `user in queryset.all()` fetches ALL members into Python memory and does a
  linear scan. `.filter(pk=...).exists()` generates SELECT 1 WHERE ... LIMIT 1.
  For a 100-member group the difference is 100 objects fetched vs 0.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsGroupAdmin(BasePermission):
    """
    Read access: any authenticated group member.
    Write access: group admin only.

    Used on GroupViewSet for list/create/update/destroy and admin-only actions.
    """

    def has_permission(self, request, view):
        """Baseline: user must be authenticated. Checked before object lookup."""
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        """
        Safe methods → member check (single EXISTS query).
        Mutating methods → admin ID comparison (no DB hit).
        """
        if request.method in SAFE_METHODS:
            return obj.members.filter(pk=request.user.pk).exists()
        return obj.admin_id == request.user.pk   # ID comparison, no DB hit


class IsMemberOfGroup(BasePermission):
    """
    Any authenticated member of the associated group.
    Works for Group, Trip, and any model with a .group FK.

    Used on TripViewSet where non-admins need read access.
    """

    def has_permission(self, request, view):
        """Baseline: user must be authenticated."""
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        """
        Resolve the group from the object and check membership.
        getattr(obj, 'group', obj) handles both Group instances
        and related objects (Trip) with a .group FK.
        """
        group = getattr(obj, 'group', obj)
        return group.members.filter(pk=request.user.pk).exists()