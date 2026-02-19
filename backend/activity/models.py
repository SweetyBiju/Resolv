from django.db import models
from django.conf import settings

class Notification(models.Model):
    """
    Tracks real-time alerts for users regarding group activity.
    """
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To {self.recipient.username}: {self.title}"

class ActivityLog(models.Model):
    """
    A permanent record of all financial and group changes for transparency.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255) # e.g., 'Updated Expense', 'Joined Group'
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(blank=True, null=True) # To store 'before' and 'after' data

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"