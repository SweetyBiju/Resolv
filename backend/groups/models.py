import uuid
from django.db import models
from django.conf import settings

class Group(models.Model):
    """
    Represents a collection of users sharing expenses.
    Uses an invite-code system for privacy and easy onboarding.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # Unique code generated on creation for group joins
    invite_code = models.CharField(max_length=10, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # The creator of the group
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='admin_groups'
    )

    def save(self, *args, **kwargs):
        # Auto-generate a unique 8-character code if it doesn't exist
        if not self.invite_code:
            self.invite_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name