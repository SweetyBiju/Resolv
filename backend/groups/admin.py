from django.contrib import admin
from .models import Group

# Group model register
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin', 'invite_code', 'created_at')
    # Search Invite code 
    search_fields = ('name', 'invite_code')