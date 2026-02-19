from django.db import models
from django.conf import settings
from groups.models import Group

class Expense(models.Model):
    """
    Core model for tracking expenditures. 
    Supports different split types for transaction flexibility.
    """
    SPLIT_TYPES = [
        ('EQUAL', 'Equal'),
        ('EXACT', 'Exact Amount'),
        ('PERCENT', 'Percentage'),
    ]

    title = models.CharField(max_length=255)
    # DecimalField is used to prevent floating-point rounding errors
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    # The user who covered the initial bill
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='paid_expenses'
    )
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    split_type = models.CharField(max_length=10, choices=SPLIT_TYPES, default='EQUAL')
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount} {self.currency}"


class ExpenseSplit(models.Model):
    """
    Maps how much each specific user owes for a given expense.
    Used for calculating net balances.
    """
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        return f"{self.user.username} owes {self.amount_owed} for {self.expense.title}"