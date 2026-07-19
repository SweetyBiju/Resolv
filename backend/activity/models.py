"""
activity/models.py
──────────────────
Three models:
  ActivityLog  — permanent, tamper-evident audit trail (wired into service layer)
  Notification — per-user read/unread alerts (dormant until async layer added)
  Dispute      — structured conflict-resolution workflow (dormant until Round 11+)
"""
from django.db import models
from django.conf import settings


class ActivityLog(models.Model):
    """
    Permanent record of all financial and group mutations.
    user → SET_NULL so the log survives user deletion (audit must not vanish).
    Written exclusively by services.py and views.py — never by hand.
    """

    ACTION_CHOICES = [
        # Expense
        ('EXPENSE_CREATED',      'Expense Created'),
        ('EXPENSE_UPDATED',      'Expense Updated'),
        # Settlement
        ('SETTLEMENT_CREATED',   'Settlement Created'),
        ('SETTLEMENT_CONFIRMED', 'Settlement Confirmed'),
        # Group membership
        ('GROUP_CREATED',        'Group Created'),
        ('GROUP_DELETED',        'Group Deleted'),
        ('MEMBER_ADDED',         'Member Added'),
        ('MEMBER_REMOVED',       'Member Removed'),
        ('MEMBER_JOINED',        'Member Joined via Invite'),
        ('INVITE_REGENERATED',   'Invite Code Regenerated'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs',
    )
    action    = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    # Stores contextual snapshot: group_id, expense_id, before/after amounts, etc.
    details   = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f"{self.user} — {self.action} at {self.timestamp}"


class Notification(models.Model):
    """
    Per-user read/unread alerts.
    DORMANT: wire in once Celery async layer is active (post-Round 9).
    CASCADE is acceptable — notifications are ephemeral, per-user data.
    """
    recipient  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title      = models.CharField(max_length=255)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"To {self.recipient.username}: {self.title}"


class Dispute(models.Model):
    """
    Structured conflict-resolution workflow.
    """
    STATUS_CHOICES = [
        ('OPEN',     'Open'),
        ('UNDER_REVIEW', 'Under Review'),
        ('RESOLVED', 'Resolved'),
        ('REJECTED', 'Rejected'),
    ]

    expense   = models.ForeignKey(
        'expenses.Expense',
        on_delete=models.PROTECT,
        related_name='disputes',
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='raised_disputes',
    )
    reason       = models.TextField()
    evidence_url = models.URLField(max_length=500, blank=True, null=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_disputes'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_response = models.TextField(blank=True, null=True)
    
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Dispute on {self.expense.title} by {self.raised_by.username}"