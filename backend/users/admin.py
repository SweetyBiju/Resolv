"""
users/admin.py
──────────────
Admin panel configuration for the users domain per plan §4.9.

ReliabilityHistoryInline is read-only — history is append-only and must
never be edited through the admin panel (that would corrupt the audit trail).
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ReliabilityHistory


class ReliabilityHistoryInline(admin.TabularInline):
    """
    Read-only inline showing a user's reliability score history.
    append-only: the admin panel cannot add or change history records.
    """
    model           = ReliabilityHistory
    extra           = 0
    can_delete      = False
    fields          = ['score', 'reason', 'created_at']
    readonly_fields = ['score', 'reason', 'created_at']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Extended UserAdmin for the custom User model.
    reliability_score is read-only — it is computed via signals, never edited directly.
    """
    model         = User
    list_display  = ['email', 'username', 'reliability_score', 'is_active', 'date_joined']
    list_filter   = ['is_active', 'is_staff']
    search_fields = ['email', 'username']
    ordering      = ['-date_joined']

    readonly_fields = ['reliability_score', 'date_joined', 'last_login']

    # Extend the default fieldsets with our custom fields
    fieldsets = UserAdmin.fieldsets + (
        ('Resolv Profile', {
            'fields': ('reliability_score', 'currency_preference', 'upi_id', 'avatar_url'),
        }),
    )

    inlines = [ReliabilityHistoryInline]