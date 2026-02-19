from django.db import models
from django.conf import settings
from groups.models import Group

class Expense(models.Model):
    """
    Core model for tracking expenditures. 
    Maintains the high-level data for any transaction within a group.
    """
    SPLIT_TYPES = [
        ('EQUAL', 'Equal'),
        ('EXACT', 'Exact Amount'),
        ('PERCENT', 'Percentage'),
        ('ITEM', 'Item-Based'), # New addition for granular grocery/bill splitting
    ]

    title = models.CharField(max_length=255)
    # Total amount of the bill
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    # Foreign Key (FK) to the user who covered the bill
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='paid_expenses'
    )
    
    # Foreign Key (FK) linking the expense to a specific Group
    group = models.ForeignKey(
        Group, 
        on_delete=models.CASCADE, 
        related_name='expenses'
    )
    
    # Optional Foreign Key to a Trip for better organization (Phase 1.5 feature)
    # Note: Ensure the Trip model is created in groups/models.py
    trip = models.ForeignKey(
        'groups.Trip', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='expenses'
    )

    split_type = models.CharField(max_length=10, choices=SPLIT_TYPES, default='EQUAL')
    receipt_url = models.URLField(max_length=500, blank=True, null=True) # For receipt transparency
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount} {self.currency}"


class ExpenseItem(models.Model):
    """
    Represents an individual line item on a larger bill (e.g., 'Milk' in a Grocery bill).
    Allows for item-by-item splitting between different friends.
    """
    expense = models.ForeignKey(
        Expense, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    name = models.CharField(max_length=255) 
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.expense.title})"


class ExpenseSplit(models.Model):
    """
    Maps how much each specific user owes for a given expense or specific item.
    Used for the final Debt Simplification calculations.
    """
    expense = models.ForeignKey(
        Expense, 
        on_delete=models.CASCADE, 
        related_name='splits'
    )
    # Optional link to a specific item for grocery-style splitting
    item = models.ForeignKey(
        ExpenseItem, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='item_splits'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.user.username} owes {self.amount_owed} for {self.expense.title}"


class Settlement(models.Model):
    """
    Tracks the actual transfer of money between two users to resolve a debt.
    Critical for updating User Reliability Scores.
    """
    debtor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_settlements'
    )
    creditor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='received_settlements'
    )
    group = models.ForeignKey(
        Group, 
        on_delete=models.CASCADE, 
        related_name='settlements'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    # Verification flag to ensure both parties agree the money was sent
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.debtor.username} -> {self.creditor.username}: {self.amount}"


class RecurringExpense(models.Model):
    """
    Template for automated expenses that repeat (e.g., Netflix, Rent).
    """
    INTERVAL_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]

    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES)
    next_occurrence = models.DateField() # When the system should generate the next Expense
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Recurring: {self.title} ({self.interval})"