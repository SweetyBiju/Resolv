"""
groups/services.py
──────────────────
All group-domain business logic lives here.
Views call services. Services call models. Nothing else.

Public functions:
  create_group()          — create group + admin membership in one transaction
  add_member()            — idempotent member addition with active-user guard
  remove_member()         — member removal with balance + admin guards
  delete_group()          — soft-delete with full-group balance guard
  join_via_invite()       — invite-code lookup → add_member
  regenerate_invite_code() — admin-only code rotation
"""
import uuid
import logging

from django.db import transaction

from .models import Group, GroupMembership

logger = logging.getLogger('resolv.groups')

EPSILON = 0.005   # mirrors expenses/utils.EPSILON — balances below this are treated as settled


# ── Group lifecycle ───────────────────────────────────────────────────────────

@transaction.atomic
def create_group(name: str, admin_user, **kwargs) -> Group:
    """
    Create a Group and a GroupMembership(role='ADMIN') for the creator.
    Both writes are in one transaction — a group without an admin member is invalid.

    Args:
        name: Group display name.
        admin_user: The User instance who will be admin and first member.
        **kwargs: Optional fields: description, currency, emoji.

    Returns:
        The newly created Group instance.
    """
    group = Group.objects.create(name=name, admin=admin_user, **kwargs)
    GroupMembership.objects.create(group=group, user=admin_user, role='ADMIN')
    return group


@transaction.atomic
def add_member(group: Group, user_to_add, added_by) -> GroupMembership:
    """
    Add a user to a group. Idempotent — returns existing membership if already a member.
    Guards against adding an inactive user.

    Args:
        group: The Group to add the user to.
        user_to_add: The User instance to add.
        added_by: The User instance performing the action (for audit log).

    Returns:
        The GroupMembership instance (new or existing).

    Raises:
        ValueError: If user_to_add is not active.
    """
    if not user_to_add.is_active:
        raise ValueError(f"User '{user_to_add.username}' is inactive and cannot be added.")

    membership, created = GroupMembership.objects.get_or_create(
        group=group,
        user=user_to_add,
        defaults={'role': 'MEMBER'},
    )
    return membership


@transaction.atomic
def remove_member(group: Group, user_to_remove, removed_by) -> None:
    """
    Remove a member from a group.
    Financial guard: the user must have a zero net balance before removal.
    Admin guard: the group admin cannot be removed — transfer admin first.

    Args:
        group: The Group to remove from.
        user_to_remove: The User instance to remove.
        removed_by: The User performing the action (for audit log).

    Raises:
        ValueError: If the user is the group admin.
        ValueError: If the user has an unsettled balance.
    """
    if user_to_remove.pk == group.admin_id:
        raise ValueError("Transfer admin rights before removing the admin.")

    from expenses.utils import compute_group_balances
    balances   = compute_group_balances(group.id)
    user_entry = next((b for b in balances if b['user_id'] == user_to_remove.pk), None)

    if user_entry and abs(float(user_entry['net_balance'])) > EPSILON:
        raise ValueError(
            f"User '{user_to_remove.username}' has an unsettled balance of "
            f"{user_entry['net_balance']}. Settle all debts before removing."
        )

    # Hard delete — GroupMembership is not financial data.
    GroupMembership.objects.filter(group=group, user=user_to_remove).delete()


@transaction.atomic
def delete_group(group: Group, deleted_by) -> None:
    """
    Soft-delete a group. Full financial guard: every member must have zero balance.

    Args:
        group: The Group to delete.
        deleted_by: The User performing the action (for audit log).

    Raises:
        ValueError: If any member has a non-zero balance, lists all unsettled members.
    """
    from expenses.utils import compute_group_balances
    balances  = compute_group_balances(group.id)
    unsettled = [
        b['username']
        for b in balances
        if abs(float(b['net_balance'])) > EPSILON
    ]
    if unsettled:
        raise ValueError(
            f"Cannot delete group — unsettled balances exist for: {', '.join(unsettled)}."
        )

    group.delete()   # calls Group.delete() → soft delete (is_active=False)


def join_via_invite(invite_code: str, user) -> Group:
    """
    Look up a group by invite code and add the user as a member.
    Idempotent — returns the group even if already a member.

    Args:
        invite_code: The raw invite code string (will be uppercased).
        user: The User joining.

    Returns:
        The Group the user joined (or is already in).

    Raises:
        ValueError: If the invite code does not match any active group.
    """
    group = Group.objects.filter(invite_code=invite_code.strip().upper()).first()
    if not group:
        raise ValueError("Invalid invite code.")

    add_member(group=group, user_to_add=user, added_by=user)
    return group


def regenerate_invite_code(group: Group, requested_by) -> str:
    """
    Generate a new invite code for the group. Admin-only.

    Args:
        group: The Group whose code is being rotated.
        requested_by: The User requesting the change.

    Returns:
        The new invite code string.

    Raises:
        PermissionError: If requested_by is not the group admin.
    """
    if requested_by.pk != group.admin_id:
        raise PermissionError("Only the group admin can regenerate the invite code.")

    group.invite_code = uuid.uuid4().hex[:8].upper()
    group.save(update_fields=['invite_code'])

    # NOTE 2 FIX: write the audit log entry that was defined but never called.
    from activity.models import ActivityLog
    ActivityLog.objects.create(
        user=requested_by,
        action='INVITE_REGENERATED',
        details={'group_id': group.id, 'group_name': group.name},
    )

    return group.invite_code


@transaction.atomic
def transfer_admin(group: Group, new_admin, requested_by) -> None:
    """
    Transfer admin rights to another member.

    Args:
        group: The Group being updated.
        new_admin: The User receiving admin rights.
        requested_by: The current admin requesting the transfer.

    Raises:
        PermissionError: If requested_by is not the group admin.
        ValueError: If new_admin is not a member of the group.
    """
    if requested_by.pk != group.admin_id:
        raise PermissionError("Only the current group admin can transfer admin rights.")

    if not group.members.filter(pk=new_admin.pk).exists():
        raise ValueError("The new admin must be a member of the group.")

    if new_admin.pk == requested_by.pk:
        raise ValueError("You are already the admin of this group.")

    # Update GroupMembership roles
    GroupMembership.objects.filter(group=group, user=requested_by).update(role='MEMBER')
    GroupMembership.objects.filter(group=group, user=new_admin).update(role='ADMIN')

    # Update Group admin FK
    group.admin = new_admin
    group.save(update_fields=['admin'])


