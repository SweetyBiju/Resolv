from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Extending the default User model to include social accountability 
    and financial preferences.
    """
    # Tracks user's history of settling debts on time
    reliability_score = models.FloatField(default=100.0) 
    # User's preferred currency for display and calculations
    currency_preference = models.CharField(max_length=3, default='INR') 
    # For quick P2P settlements via UPI
    upi_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.username