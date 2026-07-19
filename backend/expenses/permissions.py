"""
expenses/permissions.py
───────────────────────
Object-level permission for Expense mutations.

DRF calls has_permission() on every request (including list/create).
DRF calls has_object_permission() only on detail actions (retrieve/update/destroy).
Both must be defined — has_object_permission alone is silently skipped on lists.
"""

from rest_framework import permissions


class IsPayerOrGroupAdmin(permissions.BasePermission):
    """
    Read  (GET, HEAD, OPTIONS): any authenticated group member.
    Write (POST, PATCH, DELETE): only the expense payer or the group admin.

    has_permission  → guards list + create actions (no object yet).
    has_object_permission → guards retrieve + update + destroy.
    """

    def has_permission(self, request, view):
        # Authentication is enforced by IsAuthenticated in the viewset.
        # Here we simply allow all authenticated requests through to the
        # object-level check. Unauthenticated requests are already blocked.
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read access: any member of the expense's group
        if request.method in permissions.SAFE_METHODS:
            return obj.group.members.filter(pk=request.user.pk).exists()

        # Write access: payer or group admin only
        return (
            obj.paid_by_id == request.user.pk
            or obj.group.admin_id == request.user.pk
        )