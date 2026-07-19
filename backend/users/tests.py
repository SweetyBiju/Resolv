"""
users/tests.py
──────────────
Test suite covering all user domain scenarios per plan §12.2.

Tests call services directly — not HTTP — because the service layer
is the unit under test. Tests are isolated via Django's TestCase
(each test runs in a transaction that is rolled back after the test).
"""
from decimal import Decimal

from django.test import TestCase

from users.models import User, ReliabilityHistory
from users import services


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(
    email: str = 'test@test.com',
    username: str = 'testuser',
    password: str = 'ValidPass123!',
) -> User:
    """Create a standard active user via the service (hashes password correctly)."""
    return services.register_user(username=username, email=email, password=password)


# ── Registration ──────────────────────────────────────────────────────────────

class RegistrationTests(TestCase):

    def test_registration_valid(self):
        """A valid registration creates an active user with a hashed password."""
        user = make_user()
        self.assertIsNotNone(user.pk)
        self.assertTrue(user.is_active)
        # Password must be stored as a hash, not plain text
        self.assertNotEqual(user.password, 'ValidPass123!')
        self.assertTrue(user.check_password('ValidPass123!'))

    def test_registration_duplicate_email_raises(self):
        """
        Two users with the same email must raise an IntegrityError.
        Email is the USERNAME_FIELD — it must be unique at the DB level.
        """
        make_user(email='dup@test.com', username='user1')
        with self.assertRaises(Exception):
            make_user(email='dup@test.com', username='user2')

    def test_registration_sets_default_reliability_score(self):
        """New users start with a reliability score of 70.00 per the model default."""
        user = make_user()
        self.assertEqual(user.reliability_score, Decimal('70.00'))

    def test_registration_default_currency_preference(self):
        """Default currency preference is INR."""
        user = make_user()
        self.assertEqual(user.currency_preference, 'INR')


# ── Profile update ────────────────────────────────────────────────────────────

class ProfileUpdateTests(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_update_profile_with_correct_old_password(self):
        """
        Password change succeeds when old_password matches the current password.
        After the update, the new password authenticates correctly.
        """
        services.update_profile(self.user, {
            'new_password': 'NewValidPass456!',
            'old_password': 'ValidPass123!',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewValidPass456!'))

    def test_update_profile_with_wrong_old_password_raises_400(self):
        """
        UserUpdateSerializer.validate() must raise ValidationError when old_password
        is wrong. We test the serializer directly here.
        """
        from users.serializers import UserUpdateSerializer
        serializer = UserUpdateSerializer(
            instance=self.user,
            data={
                'old_password': 'WrongPassword!',
                'new_password': 'NewValidPass456!',
            },
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('old_password', serializer.errors)

    def test_update_profile_non_password_fields(self):
        """Updating username and currency_preference works without a password."""
        services.update_profile(self.user, {
            'username': 'newname',
            'currency_preference': 'USD',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newname')
        self.assertEqual(self.user.currency_preference, 'USD')


# ── Reliability score ─────────────────────────────────────────────────────────

class ReliabilityScoreTests(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_increment_reliability_score_increases_by_half(self):
        """increment_reliability_score() adds exactly 0.5 to the score."""
        initial = self.user.reliability_score  # 70.00
        services.increment_reliability_score(self.user.pk, reason='Test increment')
        self.user.refresh_from_db()
        self.assertEqual(self.user.reliability_score, initial + Decimal('0.5'))

    def test_increment_reliability_score_creates_history_record(self):
        """Every increment must create a ReliabilityHistory row."""
        services.increment_reliability_score(self.user.pk, reason='Settlement confirmed')
        history = ReliabilityHistory.objects.filter(user=self.user)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().reason, 'Settlement confirmed')

    def test_reliability_score_bounds_cannot_exceed_100(self):
        """
        Score must never exceed 100 regardless of how many increments are applied.
        Least() clamps at the DB level.
        """
        # Force score to 99.8 — two increments would naively push it to 100.8
        User.objects.filter(pk=self.user.pk).update(reliability_score=Decimal('99.8'))
        services.increment_reliability_score(self.user.pk, reason='Near cap increment')
        self.user.refresh_from_db()
        self.assertLessEqual(self.user.reliability_score, Decimal('100.00'))

    def test_reliability_score_bounds_cannot_go_below_0(self):
        """
        DB-level CheckConstraint enforces 0 ≤ score ≤ 100.
        Attempting to set score below 0 must raise an IntegrityError.
        """
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            User.objects.filter(pk=self.user.pk).update(
                reliability_score=Decimal('-1.00')
            )

    def test_soft_delete_sets_is_active_false(self):
        """
        User.delete() must not hard-delete the row. is_active → False only.
        The user must remain in the DB for financial record integrity.
        """
        self.user.delete()
        # Must still exist in raw DB (via all_objects)
        self.assertTrue(User.all_objects.filter(pk=self.user.pk).exists())
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_soft_deleted_user_excluded_from_default_queryset(self):
        """A soft-deleted user must not appear in User.objects.all()."""
        self.user.delete()
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
