"""
groups/tests.py
────────────────
Test suite covering all group domain scenarios per plan §12.2.

Uses Django's TestCase (wraps each test in a transaction rollback).
Tests call services directly — not HTTP — because the service layer is the
unit under test. View-level HTTP tests belong in integration/e2e suites.
"""
from decimal import Decimal

from django.test import TestCase

from users.models import User
from groups.models import Group, GroupMembership
from groups import services


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(email: str, username: str, password: str = 'testpass123!') -> User:
    """Create an active user for use in tests."""
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )


def make_group(admin: User, name: str = 'Test Group') -> Group:
    """Create a group with the given admin using the service (ensures admin membership)."""
    return services.create_group(name=name, admin_user=admin)


# ── Group creation ────────────────────────────────────────────────────────────

class CreateGroupTests(TestCase):

    def setUp(self):
        self.admin = make_user('admin@test.com', 'admin')

    def test_create_group_creates_admin_membership(self):
        """
        create_group() must create both the Group and a GroupMembership
        with role='ADMIN' for the creator in one atomic write.
        """
        group = make_group(self.admin)

        self.assertTrue(Group.objects.filter(pk=group.pk).exists())
        membership = GroupMembership.objects.get(group=group, user=self.admin)
        self.assertEqual(membership.role, 'ADMIN')

    def test_create_group_generates_invite_code(self):
        """invite_code must be auto-populated on creation."""
        group = make_group(self.admin)
        self.assertTrue(group.invite_code)
        self.assertEqual(len(group.invite_code), 8)

    def test_create_group_invite_code_is_unique(self):
        """Two groups must not share an invite code."""
        g1 = make_group(self.admin, name='Group 1')
        g2 = make_group(self.admin, name='Group 2')
        self.assertNotEqual(g1.invite_code, g2.invite_code)


# ── Invite code join ──────────────────────────────────────────────────────────

class JoinViaInviteTests(TestCase):

    def setUp(self):
        self.admin  = make_user('admin@test.com', 'admin')
        self.member = make_user('member@test.com', 'member')
        self.group  = make_group(self.admin)

    def test_join_via_invite_code(self):
        """A user with a valid invite code becomes a member."""
        services.join_via_invite(self.group.invite_code, self.member)
        self.assertTrue(
            GroupMembership.objects.filter(group=self.group, user=self.member).exists()
        )

    def test_join_duplicate_is_idempotent(self):
        """Joining twice does not raise or create a duplicate membership."""
        services.join_via_invite(self.group.invite_code, self.member)
        services.join_via_invite(self.group.invite_code, self.member)  # second call
        count = GroupMembership.objects.filter(group=self.group, user=self.member).count()
        self.assertEqual(count, 1)

    def test_join_invalid_invite_code_raises(self):
        """An invalid invite code must raise ValueError, not silently fail."""
        with self.assertRaises(ValueError):
            services.join_via_invite('BADCODE1', self.member)

    def test_join_new_member_gets_member_role(self):
        """A user who joins via invite must have role='MEMBER', not 'ADMIN'."""
        services.join_via_invite(self.group.invite_code, self.member)
        membership = GroupMembership.objects.get(group=self.group, user=self.member)
        self.assertEqual(membership.role, 'MEMBER')


# ── Member removal ────────────────────────────────────────────────────────────

class RemoveMemberTests(TestCase):

    def setUp(self):
        self.admin  = make_user('admin@test.com', 'admin')
        self.member = make_user('member@test.com', 'member')
        self.group  = make_group(self.admin)
        services.add_member(self.group, self.member, self.admin)

    def test_remove_member_with_zero_balance_succeeds(self):
        """A member with zero balance can be removed."""
        services.remove_member(self.group, self.member, self.admin)
        self.assertFalse(
            GroupMembership.objects.filter(group=self.group, user=self.member).exists()
        )

    def test_remove_admin_raises(self):
        """Attempting to remove the group admin raises ValueError."""
        with self.assertRaises(ValueError, msg="Transfer admin rights before removing the admin."):
            services.remove_member(self.group, self.admin, self.admin)

    def test_remove_member_with_unsettled_balance_raises(self):
        """
        A member with an unsettled balance (non-zero net_balance) cannot be removed.
        We simulate a balance by patching compute_group_balances.
        """
        from unittest.mock import patch
        from decimal import Decimal

        fake_balances = [
            {'user_id': self.member.pk, 'username': 'member', 'net_balance': Decimal('-100.00')},
            {'user_id': self.admin.pk,  'username': 'admin',  'net_balance': Decimal('100.00')},
        ]
        with patch('expenses.utils.compute_group_balances', return_value=fake_balances):
            with self.assertRaises(ValueError):
                services.remove_member(self.group, self.member, self.admin)


# ── Group deletion ────────────────────────────────────────────────────────────

class DeleteGroupTests(TestCase):

    def setUp(self):
        self.admin = make_user('admin@test.com', 'admin')
        self.group = make_group(self.admin)

    def test_delete_group_with_zero_balances_soft_deletes(self):
        """delete_group() with all-zero balances sets is_active=False."""
        services.delete_group(self.group, self.admin)
        self.group.refresh_from_db()
        self.assertFalse(self.group.is_active)

    def test_delete_group_excluded_from_default_queryset(self):
        """A soft-deleted group must not appear in Group.objects.all()."""
        services.delete_group(self.group, self.admin)
        self.assertFalse(Group.objects.filter(pk=self.group.pk).exists())

    def test_delete_group_visible_in_all_objects(self):
        """A soft-deleted group must be accessible via Group.all_objects."""
        services.delete_group(self.group, self.admin)
        self.assertTrue(Group.all_objects.filter(pk=self.group.pk).exists())

    def test_delete_group_with_unsettled_balances_raises(self):
        """delete_group() raises ValueError if any member has a non-zero balance."""
        from unittest.mock import patch
        from decimal import Decimal

        fake_balances = [
            {'user_id': self.admin.pk, 'username': 'admin', 'net_balance': Decimal('50.00')},
        ]
        with patch('expenses.utils.compute_group_balances', return_value=fake_balances):
            with self.assertRaises(ValueError):
                services.delete_group(self.group, self.admin)


# ── Invite code visibility ────────────────────────────────────────────────────

class InviteCodeVisibilityTests(TestCase):

    def setUp(self):
        self.admin  = make_user('admin@test.com', 'admin')
        self.member = make_user('member@test.com', 'member')
        self.group  = make_group(self.admin)
        services.add_member(self.group, self.member, self.admin)

    def test_invite_code_not_visible_to_non_admin(self):
        """
        GroupSerializer (member view) must not include invite_code.
        GroupAdminSerializer (admin view) must include it.
        """
        from groups.serializers import GroupSerializer, GroupAdminSerializer

        member_data = GroupSerializer(self.group).data
        admin_data  = GroupAdminSerializer(self.group).data

        self.assertNotIn('invite_code', member_data)
        self.assertIn('invite_code', admin_data)

    def test_regenerate_invite_code(self):
        """regenerate_invite_code() returns a new code and persists it."""
        old_code = self.group.invite_code
        new_code = services.regenerate_invite_code(self.group, self.admin)
        self.group.refresh_from_db()

        self.assertNotEqual(old_code, new_code)
        self.assertEqual(self.group.invite_code, new_code)

    def test_non_admin_cannot_regenerate_invite_code(self):
        """Only the group admin can regenerate the invite code."""
        with self.assertRaises(PermissionError):
            services.regenerate_invite_code(self.group, self.member)
