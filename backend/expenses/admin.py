from django.contrib import admin
from .models import Expense, ExpenseSplit

# Expense and split
class ExpenseSplitInline(admin.TabularInline):
    model = ExpenseSplit
    extra = 0 

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'paid_by', 'group', 'split_type', 'date')
    inlines = [ExpenseSplitInline] 

admin.site.register(ExpenseSplit)