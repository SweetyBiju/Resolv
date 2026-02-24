from django.contrib import admin
from .models import Notification, ActivityLog, Dispute

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for User Notifications.
    Allows for quick filtering of read/unread alerts.
    """
    # Columns to display in the main list view
    list_display = ('recipient', 'title', 'is_read', 'created_at')
    # Filter sidebar for easy management
    list_filter = ('is_read', 'created_at')
    # Search functionality for finding specific alerts
    search_fields = ('recipient__username', 'title', 'message')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for the System Audit Trail.
    Read-only settings are recommended for logs to preserve data integrity.
    """
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('timestamp', 'action')
    search_fields = ('user__username', 'action', 'details')
    
    # Making fields read-only prevents manual tampering with audit logs
    readonly_fields = ('user', 'action', 'timestamp', 'details')

    # Disabling the ability to manually add logs via Admin for security
    def has_add_permission(self, request):
        return False
    


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('expense', 'raised_by', 'status', 'created_at')
    list_filter = ('status',)