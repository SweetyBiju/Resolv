from django.contrib import admin
from .models import Group, Trip

class TripInline(admin.TabularInline):
    """Shows all trips belonging to a group inside the group page."""
    model = Trip
    extra = 0

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin', 'invite_code', 'created_at')
    search_fields = ('name', 'invite_code')
    inlines = [TripInline]

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'group')