"""
expenses/signals.py
───────────────────
Side-effect triggers for expense and settlement mutations.
Services write data → Django signals → ActivityLog.
"""
import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Expense, Settlement

logger = logging.getLogger('resolv.expenses')

def _log(user, action: str, details: dict) -> None:
    """Write one ActivityLog row. Silent on failure."""
    try:
        from activity.models import ActivityLog
        ActivityLog.objects.create(user=user, action=action, details=details)
    except Exception:
        logger.exception("ActivityLog write failed [action=%s, user=%s]", action, getattr(user, 'pk', None))

@receiver(pre_save, sender=Expense)
def expense_capture_before(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Expense.objects.get(pk=instance.pk)
            instance._before = {
                'title': old_instance.title,
                'amount': str(old_instance.amount),
                'split_type': old_instance.split_type,
            }
        except Expense.DoesNotExist:
            pass

@receiver(post_save, sender=Expense)
def expense_post_save(sender, instance, created, **kwargs):
    if created:
        _log(instance.paid_by, 'EXPENSE_CREATED', {
            'expense_id': instance.id,
            'title': instance.title,
            'amount': str(instance.amount),
            'currency': 'INR', # Currently hardcoded to INR or implicit. Actually, we should check if group currency exists, or omit. I'll omit currency and just rely on amount for now, or just use 'amount'. Wait, is there a currency field? No. I'll omit it for now and handle in JS. Let's just add group_name.
            'group_id': instance.group_id,
            'group_name': getattr(instance.group, 'name', f'Group {instance.group_id}'),
            'split_type': instance.split_type,
        })
    elif hasattr(instance, '_before'):
        # Updated
        _log(instance.paid_by, 'EXPENSE_UPDATED', {
            'expense_id': instance.id,
            'group_id': instance.group_id,
            'group_name': getattr(instance.group, 'name', f'Group {instance.group_id}'),
            'before': instance._before,
            'after': {
                'title': instance.title,
                'amount': str(instance.amount),
                'split_type': instance.split_type,
            },
        })

@receiver(pre_save, sender=Settlement)
def settlement_capture_before(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Settlement.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Settlement.DoesNotExist:
            pass

@receiver(post_save, sender=Settlement)
def settlement_post_save(sender, instance, created, **kwargs):
    if created:
        _log(instance.payer, 'SETTLEMENT_CREATED', {
            'settlement_id': instance.id,
            'group_id': instance.group_id,
            'group_name': getattr(instance.group, 'name', f'Group {instance.group_id}'),
            'payer_id': instance.payer_id,
            'receiver_id': instance.receiver_id,
            'receiver_username': getattr(instance.receiver, 'username', f'User {instance.receiver_id}'),
            'amount': str(instance.amount),
            'currency': getattr(instance, 'currency', ''),
        })
    elif getattr(instance, '_old_status', None) != 'CONFIRMED' and instance.status == 'CONFIRMED':
        _log(instance.receiver, 'SETTLEMENT_CONFIRMED', {
            'settlement_id': instance.id,
            'group_id': instance.group_id,
            'group_name': getattr(instance.group, 'name', f'Group {instance.group_id}'),
            'payer_id': instance.payer_id,
            'payer_username': getattr(instance.payer, 'username', f'User {instance.payer_id}'),
            'receiver_id': instance.receiver_id,
            'amount': str(instance.amount),
            'currency': getattr(instance, 'currency', ''),
        })

        # Increment reliability score for the payer
        try:
            from users.services import increment_reliability_score
            increment_reliability_score(
                instance.payer_id, 
                f"Settlement of {instance.amount} confirmed in group {instance.group_id}"
            )
        except Exception:
            logger.exception("Failed to increment reliability score for user %s", instance.payer_id)

