from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CheckConstraint, Q
from decimal import Decimal
from .managers import ActiveUserManager
from django.contrib.auth.models import UserManager


class User(AbstractUser):

    email = models.EmailField(unique=True)

    # authenticate via email
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']  # username still required but not the login key

    objects = ActiveUserManager()
    all_objects = UserManager()

    reliability_score     = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('70.00')
    )
    #  Remove settlement_count — computed via annotation, never stored
    currency_preference   = models.CharField(max_length=3, default='INR')
    upi_id                = models.CharField(max_length=50, blank=True, null=True)
    avatar_url            = models.URLField(blank=True, null=True)  #  null not ''

    def delete(self, *args, **kwargs):
        # AbstractUser.is_active already exists —soft-delete
        self.is_active = False
        self.save(update_fields=['is_active'])

    class Meta:
        constraints = [
            CheckConstraint(                                  
                condition=Q(reliability_score__gte=0) & Q(reliability_score__lte=100),
                name='reliability_score_within_bounds'
            ),
        ]

    def __str__(self):
        return self.email


class ReliabilityHistory(models.Model):
    user      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  related_name='score_history')
    score     = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    reason    = models.CharField(max_length=255)

    class Meta:
        indexes = [                                           
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['-created_at']