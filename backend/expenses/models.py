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
        ('ITEM', 'Item-Based'), 
    ]

    CATEGORY_CHOICES = [
        ('FOOD', 'Food & Drink'),
        ('TRAVEL', 'Travel'),
        ('HOUSING', 'Housing'),
        ('ENTERTAINMENT', 'Entertainment'),
        ('OTHER', 'Other'),
    ]

    title = models.CharField(max_length=255)
    # Total amount of the bill
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER') # ADDED: For Analytics Dashboard

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
    is_active = models.BooleanField(default=True)

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()

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
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_settlements'
    )
    receiver = models.ForeignKey(
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
    status = models.CharField(max_length=20, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()

    def __str__(self):
        return f"{self.payer.username} -> {self.receiver.username}: {self.amount}"


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




class ApprovalWorkflow(models.Model):
    """
     Controls for transactions above a price threshold.
    Ensures group consensus for large purchases.
    """
    # One-to-One relationship: Each expense has at most one approval status
    expense = models.OneToOneField(
        'Expense', 
        on_delete=models.CASCADE, 
        related_name='approval'
    )
    is_approved = models.BooleanField(default=False)
    # List of users who have approved this specific expense
    approvers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='approved_expenses',
        blank=True
    )
    # Metadata for the audit trail [cite: 67]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Approval for {self.expense.title} - Status: {self.is_approved}"