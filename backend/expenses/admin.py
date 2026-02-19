from django.contrib import admin
from .models import Expense, ExpenseItem, ExpenseSplit, Settlement, RecurringExpense

class ExpenseItemInline(admin.TabularInline):
    """Allows adding grocery items directly inside the Expense page."""
    model = ExpenseItem
    extra = 1

class ExpenseSplitInline(admin.TabularInline):
    """Allows adding user splits directly inside the Expense page."""
    model = ExpenseSplit
    extra = 1

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """
    Admin configuration for Expenses.
    Displays items and splits as inlines for better visibility.
    """
    list_display = ('title', 'amount', 'currency', 'paid_by', 'group', 'trip', 'split_type', 'date')
    list_filter = ('group', 'split_type', 'date', 'currency')
    search_fields = ('title', 'paid_by__username')
    # Combining everything into one view for a 'Pro' experience
    inlines = [ExpenseItemInline, ExpenseSplitInline]

@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    """Tracks direct P2P payments between users."""
    list_display = ('debtor', 'creditor', 'amount', 'currency', 'is_confirmed', 'created_at')
    list_filter = ('is_confirmed', 'currency')
    search_fields = ('debtor__username', 'creditor__username')

@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    """Manages automated subscription and rent templates."""
    list_display = ('title', 'amount', 'interval', 'next_occurrence', 'is_active')
    list_filter = ('interval', 'is_active')

# Registering these individually as well for direct management
admin.site.register(ExpenseItem)
admin.site.register(ExpenseSplit)