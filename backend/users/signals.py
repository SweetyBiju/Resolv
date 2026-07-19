from django.db.models import signals
from django.dispatch import receiver
from .models import User

# Placeholder for future events like password change or avatar update
# @receiver(signals.post_save, sender=User)
# def user_post_save(sender, instance, created, **kwargs):
#     pass
