from rest_framework import permissions

class IsGroupAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admins of a group to modify it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any member, but edits/deletes require admin status
        if request.method in permissions.SAFE_METHODS:
            return request.user in obj.members.all()
        return obj.admin == request.user