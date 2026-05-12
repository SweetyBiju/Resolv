from rest_framework import permissions

class IsPayerOrGroupAdmin(permissions.BasePermission):
    """
    Custom permission: Only the payer or the group admin can modify/delete the expense.
    Read access is granted to all group members.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user in obj.group.members.all()
        
        # Write permissions: Must be the payer OR the group admin
        return obj.paid_by == request.user or obj.group.admin == request.user