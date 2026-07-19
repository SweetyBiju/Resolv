from django.contrib import admin
from .models import Budget

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'category', 'amount_limit', 'month', 'year')
    list_filter = ('category', 'month', 'year')
    search_fields = ('user__username', 'group__name')
