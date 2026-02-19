from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Custom UserAdmin 
class CustomUserAdmin(UserAdmin):
    model = User
    # Admin panel list
    list_display = ['username', 'email', 'reliability_score', 'is_staff']
    # extra fields
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('reliability_score', 'currency_preference', 'upi_id')}),
    )

admin.site.register(User, CustomUserAdmin)