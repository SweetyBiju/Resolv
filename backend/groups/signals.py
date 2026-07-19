"""
groups/signals.py
─────────────────
Side-effect triggers for group and membership mutations.
Services write data → Django signals → ActivityLog + Celery task.

Why signals, not inline service calls:
  Services should not know about Celery infrastructure or the activity domain.
  Signals decouple the domain write from its consequences, keeping services
  independently testable and reusable.

Signal handlers that write to the audit trail use try/except with silent
failure — a logging error must never abort a group operation.
"""
import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Group, GroupMembership

logger = logging.getLogger('resolv.groups')


def _log(user, action: str, details: dict) -> None:
    """
    Write one ActivityLog row. Deferred import avoids circular imports.
    Silent on failure — audit loss is preferable to aborting the user-facing action.
    """
    try:
        from activity.models import ActivityLog
        ActivityLog.objects.create(user=user, action=action, details=details)
    except Exception:
        logger.exception(
            "ActivityLog write failed [action=%s, user=%s]",
            action, getattr(user, 'pk', None),
        )


@receiver(post_save, sender=GroupMembership)
def membership_post_save(sender, instance, created, **kwargs):
    """
    Fires after a GroupMembership row is created.
    - Triggers balance recomputation (membership change affects the balance graph).
    - Writes ActivityLog: MEMBER_ADDED or MEMBER_JOINED depending on context.
      The service sets instance._joined_via_invite=True on invite joins.
    """
    if not created:
        return  # role updates don't need balance recompute or log

    try:
        from expenses.tasks import recompute_group_balances
        recompute_group_balances.delay(instance.group_id)
    except Exception:
        logger.exception(
            "recompute_group_balances task failed to queue for group=%s",
            instance.group_id,
        )

    action  = 'MEMBER_JOINED' if getattr(instance, '_joined_via_invite', False) else 'MEMBER_ADDED'
    details = {
        'group_id':   instance.group_id,
        'group_name': getattr(instance.group, 'name', f'Group {instance.group_id}'),
        'user_id':    instance.user_id,
        'role':       instance.role,
    }
    _log(instance.user, action, details)


@receiver(post_delete, sender=GroupMembership)
def membership_post_delete(sender, instance, **kwargs):
    """
    Fires after a GroupMembership row is hard-deleted.
    Triggers balance recomputation and writes MEMBER_REMOVED ActivityLog.
    """
    try:
        from expenses.tasks import recompute_group_balances
        recompute_group_balances.delay(instance.group_id)
    except Exception:
        logger.exception(
            "recompute_group_balances task failed to queue for group=%s",
            instance.group_id,
        )

    _log(instance.user, 'MEMBER_REMOVED', {
        'group_id': instance.group_id,
        'group_name': getattr(instance.group, 'name', f'Group {instance.group_id}'),
        'user_id':  instance.user_id,
    })


@receiver(post_save, sender=Group)
def group_post_save(sender, instance, created, **kwargs):
    """
    Fires after a Group row is created or updated.
    - created=True  → ACTIVITY: GROUP_CREATED
    - is_active=False (soft delete) → ACTIVITY: GROUP_DELETED
    No action on other updates (name change, emoji, etc.) — not audit-worthy.
    """
    if created:
        _log(instance.admin, 'GROUP_CREATED', {
            'group_id':   instance.pk,
            'group_name': instance.name,
        })
    elif not instance.is_active:
        _log(instance.admin, 'GROUP_DELETED', {
            'group_id':   instance.pk,
            'group_name': instance.name,
        })
