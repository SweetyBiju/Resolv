from django.contrib import admin
from .models import Group, GroupMembership


class GroupMembershipInline(admin.TabularInline):
    """Shows all memberships for a group inline on the Group admin page."""
    model  = GroupMembership
    extra  = 0
    fields = ['user', 'role', 'joined_at']
    readonly_fields = ['joined_at']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display   = ('name', 'admin', 'currency', 'invite_code', 'is_active', 'created_at')
    list_filter    = ('is_active', 'currency')
    search_fields  = ('name', 'invite_code')
    readonly_fields = ('invite_code', 'created_at')
    inlines        = [GroupMembershipInline]