from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Extending the default User model to include social accountability 
    and financial preferences.
    """

    email = models.EmailField(unique=True)

    # Tracks user's history of settling debts on time
    reliability_score = models.DecimalField(max_digits=5, decimal_places=2,default=70.0) 
    settlement_count = models.PositiveIntegerField(default=0)
    
    # User's preferred currency for display and calculations
    currency_preference = models.CharField(max_length=3, default='INR') 
    
    # For quick P2P settlements via UPI
    upi_id = models.CharField(max_length=50, blank=True, null=True)

    avatar_url = models.URLField(blank=True, null=True)


    def delete(self, *args, **kwargs):
        """
        FIXED: Soft delete implementation.
        Disables the account without destroying historical expense/settlement records.
        """
        self.is_active = False
        self.save()

    def __str__(self):
        return self.username
    

class ReliabilityHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='score_history')
    score = models.DecimalField(max_digits=5, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255) # e.g., "Settled debt on time"