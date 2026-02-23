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

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='joined_groups',
        blank=True
    )

    def save(self, *args, **kwargs):
        # Auto-generate a unique 8-character code if it doesn't exist
        if not self.invite_code:
            self.invite_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    



class Trip(models.Model):
    """
    A specific event or sub-category within a group (e.g., 'Goa Trip 2026').
    Allows for scoping expenses to specific dates and titles.
    """
    # Foreign Key (FK) to the parent Group
    group = models.ForeignKey(
        'Group', 
        on_delete=models.CASCADE, 
        related_name='trips'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Metadata for the trip duration
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Each trip can have its own base currency
    currency = models.CharField(max_length=3, default='INR')
    
    # Status to track if the trip is currently ongoing
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.group.name})"
    




class Budget(models.Model):
    """Shared group budgets with proactive utilization tracking.
    Helps in financial discipline for group events or trips.
    """
    group = models.ForeignKey(
        'Group', 
        on_delete=models.CASCADE, 
        related_name='budgets'
    )
    # Budget can be scoped to a specific Trip or the whole Group [cite: 86]
    trip = models.ForeignKey(
        'Trip', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='budgets'
    )
    category = models.CharField(max_length=50, default='General') # e.g., Food, Travel
    amount_limit = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Flags for Celery tasks to send one-time alerts at specific thresholds [cite: 86]
    alert_75_sent = models.BooleanField(default=False)
    alert_90_sent = models.BooleanField(default=False)
    alert_100_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Budget: {self.category} for {self.group.name}"