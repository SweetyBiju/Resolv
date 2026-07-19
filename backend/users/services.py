"""
users/services.py
─────────────────
All user-domain business logic lives here.
Views call services. Services call models. Nothing else.

Public functions:
  register_user()              — single entry point for user creation
  update_profile()             — profile update with optional password guard
  increment_reliability_score() — F()-based atomic score increment + history record
"""
import logging
from decimal import Decimal

from django.db.models import F
from django.db.models.functions import Least   # correct import path

from .models import User, ReliabilityHistory

logger = logging.getLogger('resolv.users')


def register_user(username: str, email: str, password: str, **kwargs) -> User:
    """
    Single entry point for user creation. Called by RegisterView.
    Wraps create_user() to ensure the password is always hashed correctly.

    Args:
        username: Display name.
        email: Login identifier (unique).
        password: Plain-text password — hashed by create_user().
        **kwargs: Optional fields: currency_preference, upi_id, avatar_url.

    Returns:
        The newly created User instance.
    """
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
        **kwargs,
    )


def update_profile(user: User, validated_data: dict) -> User:
    """
    Update allowed profile fields. Handles optional password change.
    Called by UserMeView PATCH.

    The old_password guard is enforced in UserUpdateSerializer.validate()
    before this function is called — no re-checking needed here.

    Args:
        user: The User instance to update.
        validated_data: Pre-validated dict from UserUpdateSerializer.

    Returns:
        The updated User instance.
    """
    validated_data.pop('old_password', None)    # already validated, not stored
    new_password = validated_data.pop('new_password', None)

    if new_password:
        user.set_password(new_password)

    for key, value in validated_data.items():
        setattr(user, key, value)

    user.save()
    return user


def increment_reliability_score(user_id: int, reason: str) -> None:
    """
    Atomically increment a user's reliability score by 0.5, clamped to 100.
    Creates a ReliabilityHistory record for the audit trail.

    Called by expenses/signals.py on SETTLEMENT_CONFIRMED.

    Why F() + Least() instead of Python arithmetic:
      F() pushes the expression to the DB, so two concurrent settlements
      confirming simultaneously cannot both read the same stale score and
      each add 0.5 independently (which would drop one increment). The DB
      handles the atomicity.

    Args:
        user_id: PK of the user whose score is being incremented.
        reason:  Human-readable reason string stored in ReliabilityHistory.
    """
    updated = User.objects.filter(pk=user_id).update(
        reliability_score=Least(
            F('reliability_score') + Decimal('0.5'),
            Decimal('100.00'),
        )
    )
    if not updated:
        logger.warning("increment_reliability_score: user_id=%s not found.", user_id)
        return

    # Re-fetch to get the DB-computed score for the history record.
    user = User.objects.get(pk=user_id)
    ReliabilityHistory.objects.create(
        user=user,
        score=user.reliability_score,
        reason=reason,
    )
