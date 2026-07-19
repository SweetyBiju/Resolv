"""
expenses/models.py
──────────────────
Four models, one domain:

  Expense       — a financial event paid by one user, split among members
  ExpenseItem   — a line item within an ITEM-type expense
  ExpenseSplit  — one member's share of an expense (or a specific item)
  Settlement    — a record of one user paying another to clear a debt

Design rules:
  - All money fields use DecimalField — no floats, ever.
  - Soft delete on Expense and Settlement via is_active flag.
  - FK guards (PROTECT) prevent silent data loss on financial records.
  - Every constraint is enforced at the DB level, not just application level.
"""

import datetime

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from .managers import ActiveManager, AllObjectsManager


# ── Expense ───────────────────────────────────────────────────────────────────

class Expense(models.Model):

    SPLIT_TYPES = [
        ('EQUAL',   'Equal'),
        ('EXACT',   'Exact Amount'),
        ('PERCENT', 'Percentage'),
        ('ITEM',    'Item-Based'),
    ]

    CATEGORY_CHOICES = [
        ('FOOD',          'Food & Drink'),
        ('TRAVEL',        'Travel'),
        ('HOUSING',       'Housing'),
        ('ENTERTAINMENT', 'Entertainment'),
        ('UTILITIES',     'Utilities'),
        ('OTHER',         'Other'),
    ]

    # ── Core fields ───────────────────────────────────────────────────────────
    title      = models.CharField(max_length=255)
    amount     = models.DecimalField(max_digits=12, decimal_places=2)
    currency   = models.CharField(max_length=3, default='INR')
    category   = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    split_type = models.CharField(max_length=10, choices=SPLIT_TYPES, default='EQUAL')
    notes      = models.TextField(blank=True, default='')      # optional context/description
    receipt_url = models.URLField(max_length=500, blank=True, null=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,           # financial record must survive user deletion
        related_name='paid_expenses',
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.PROTECT,           # expense cannot outlive its group
        related_name='expenses',
    )

    # ── Timestamps & soft delete ──────────────────────────────────────────────
    date       = models.DateField(default=datetime.date.today)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True, db_index=True)

    # ── Managers ──────────────────────────────────────────────────────────────
    objects     = ActiveManager()       # default: active only
    all_objects = AllObjectsManager()   # admin/audit: includes soft-deleted

    def delete(self, *args, **kwargs):
        """Soft delete — never hard-deletes. Use all_objects to see deleted records."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['group', 'is_active']),
            models.Index(fields=['paid_by']),
            models.Index(fields=['date']),
            models.Index(fields=['group', 'date']),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(amount__gt=0),
                name='expense_amount_must_be_positive',
            ),
        ]

    def __str__(self):
        return f"{self.title} — {self.amount} {self.currency}"


# ── ExpenseItem ───────────────────────────────────────────────────────────────

class ExpenseItem(models.Model):
    """
    A single line item within an ITEM-type expense.
    e.g. "Pizza — 400 INR", "Drinks — 200 INR"

    Each item is then split among a subset of members via ExpenseSplit.
    Only created when expense.split_type == 'ITEM'.
    """

    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,           # items are owned by the expense
        related_name='items',
    )
    name   = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            CheckConstraint(
                condition=Q(amount__gt=0),
                name='expense_item_amount_must_be_positive',
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.amount} (Expense #{self.expense_id})"


# ── ExpenseSplit ──────────────────────────────────────────────────────────────

class ExpenseSplit(models.Model):
    """
    One member's share of an expense.

    For EQUAL / EXACT / PERCENT splits: item is null, one row per member.
    For ITEM splits: item is set, one row per (member, item) pair.

    PROTECT on user: split history must survive user deletion.
    The UniqueConstraint prevents double-splits for non-item expenses.
    """

    expense     = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='splits',
    )
    item = models.ForeignKey(
        ExpenseItem,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='item_splits',
    )
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,           # split record must survive user deletion
    )
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['expense']),
        ]
        constraints = [
            UniqueConstraint(
                fields=['expense', 'user'],
                condition=Q(item__isnull=True),
                name='unique_split_per_user_per_expense',
            ),
            CheckConstraint(
                condition=Q(amount_owed__gt=0),
                name='split_amount_must_be_positive',
            ),
        ]

    def __str__(self):
        return f"{self.user} owes {self.amount_owed} for '{self.expense.title}'"


# ── Settlement ────────────────────────────────────────────────────────────────

class Settlement(models.Model):
    """
    A record of one user paying another to clear a debt.

    Lifecycle: PENDING → CONFIRMED (by receiver) or CANCELLED (by payer).
    REJECTED is kept as a choice for future dispute integration.

    All FKs are PROTECT — settlement records must never vanish silently.
    Self-settlement is blocked at both DB and serializer level.
    """

    STATUS_CHOICES = [
        ('PENDING',   'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED',  'Rejected'),      # reserved for dispute workflow
    ]

    payer    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sent_settlements',
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='received_settlements',
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.PROTECT,
        related_name='settlements',
    )

    amount   = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True, db_index=True)

    objects     = ActiveManager()
    all_objects = AllObjectsManager()

    def delete(self, *args, **kwargs):
        """Soft delete — status becomes CANCELLED, record is preserved."""
        self.is_active = False
        self.status    = 'CANCELLED'
        self.save(update_fields=['is_active', 'status', 'updated_at'])

    class Meta:
        indexes = [
            models.Index(fields=['payer', 'receiver']),
            models.Index(fields=['group', 'status']),
            models.Index(fields=['status']),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(amount__gt=0),
                name='settlement_amount_must_be_positive',
            ),
            CheckConstraint(
                condition=~Q(payer=models.F('receiver')),
                name='settlement_payer_receiver_must_differ',
            ),
        ]

    def __str__(self):
        return (
            f"{self.payer} → {self.receiver} | "
            f"{self.amount} {self.currency} | {self.status}"
        )