"""
expenses/admin.py
─────────────────
Admin configuration for the expenses app.
Inlines give a full picture of an expense (items + splits) on one page.
ActivityLog entries are read-only — no manual creation or editing allowed.
"""

from django.contrib import admin

from .models import Expense, ExpenseItem, ExpenseSplit, Settlement


# ── Inlines ───────────────────────────────────────────────────────────────────

class ExpenseItemInline(admin.TabularInline):
    model  = ExpenseItem
    extra  = 0             # don't show empty extra rows by default
    fields = ['name', 'amount']


class ExpenseSplitInline(admin.TabularInline):
    model  = ExpenseSplit
    extra  = 0
    fields = ['user', 'amount_owed', 'item']
    readonly_fields = ['item']     # item is set programmatically, not manually


# ── Expense ───────────────────────────────────────────────────────────────────

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display   = ('title', 'amount', 'currency', 'category', 'paid_by', 'group', 'split_type', 'date', 'is_active')
    list_filter    = ('split_type', 'category', 'currency', 'is_active', 'date')
    search_fields  = ('title', 'paid_by__username', 'group__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines        = [ExpenseItemInline, ExpenseSplitInline]

    def get_queryset(self, request):
        # Show all records including soft-deleted in admin
        return self.model.all_objects.all()


# ── Settlement ────────────────────────────────────────────────────────────────

@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display  = ('payer', 'receiver', 'amount', 'currency', 'status', 'group', 'created_at', 'is_active')
    list_filter   = ('status', 'currency', 'is_active')
    search_fields = ('payer__username', 'receiver__username', 'group__name')  # fixed typo: receiverr
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return self.model.all_objects.all()