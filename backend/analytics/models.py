from django.db import models
from django.conf import settings

class Budget(models.Model):
    CATEGORY_CHOICES = [                      
        ('FOOD', 'Food & Drink'),
        ('TRAVEL', 'Travel'),
        ('HOUSING', 'Housing'),
        ('ENTERTAINMENT', 'Entertainment'),
        ('UTILITIES', 'Utilities'),
        ('OTHER', 'Other'),
        ('GENERAL', 'General'),
    ]

    user          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budgets')
    group         = models.ForeignKey('groups.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='budgets')
    category      = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GENERAL')
    amount_limit  = models.DecimalField(max_digits=12, decimal_places=2)
    month         = models.IntegerField()
    year          = models.IntegerField()

    alert_thresholds_sent = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'group', 'category', 'month', 'year'],
                name='unique_budget_per_user_category_time'
            ),
        ]

    def __str__(self):
        return f"Budget: {self.category} - {self.month}/{self.year}"
