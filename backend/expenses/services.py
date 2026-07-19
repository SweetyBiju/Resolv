"""
expenses/services.py
────────────────────
All expense and settlement business logic lives here.
Views call services. Services call models. Nothing else calls models directly.

Public functions:
  create_expense_with_splits()  — atomic expense + split creation
  update_expense_with_splits()  — atomic expense + split replacement
  confirm_settlement()          — atomic confirmation with guards + scoring
  get_blocking_settlements()    — pre-delete safety check (reused in views)

Private helpers:
  _create_splits()          — split builder, called by create and update only
  _compute_pairwise_debt()  — over-settlement guard computation
  _log()                    — activity log writer
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from .models import Expense, ExpenseItem, ExpenseSplit, Settlement
from users.models import User

logger        = logging.getLogger('resolv.expenses')
CURRENCY_UNIT = Decimal('0.01')



# ── Expense creation ──────────────────────────────────────────────────────────

@transaction.atomic
def create_expense_with_splits(
    title: str,
    amount: Decimal,
    group,
    paid_by: User,
    split_type: str,
    split_data: list,
    **kwargs,
) -> Expense:
    """
    Create an Expense and all ExpenseSplit rows in one atomic transaction.
    Either everything commits or nothing does.

    split_data is already validated by ExpenseWriteSerializer before this is called.
    **kwargs accepts: currency, category, notes, receipt_url, date, trip
    """
    expense = Expense.objects.create(
        title=title,
        amount=amount,
        group=group,
        paid_by=paid_by,
        split_type=split_type,
        **kwargs,
    )
    _create_splits(expense, split_data)

    return expense


@transaction.atomic
def update_expense_with_splits(
    expense: Expense,
    validated_data: dict,
    split_data: list,
) -> Expense:
    """
    Update expense fields and replace all splits atomically.
    Old splits are deleted and new ones bulk-inserted in the same transaction.

    Actor is logged as expense.paid_by — signature intentionally unchanged
    to avoid breaking the established service contract.
    """
    for attr, value in validated_data.items():
        setattr(expense, attr, value)
    expense.save()

    expense.splits.all().delete()
    _create_splits(expense, split_data)

    return expense


# ── Split builder (private) ───────────────────────────────────────────────────

def _create_splits(expense: Expense, split_data: list) -> None:
    """
    Compute and bulk-insert ExpenseSplit rows.
    Called only from create and update — never directly from views.

    split_data is pre-validated by the serializer. Raises ValueError only
    as a last-resort guard against corrupted data reaching this layer.
    """
    splits_to_create = []

    if expense.split_type == 'EQUAL':
        members      = list(expense.group.members.all())
        member_count = len(members)
        if member_count == 0:
            logger.warning(
                "Expense %d created for empty group %d — no splits generated.",
                expense.id, expense.group_id,
            )
            return
        share = (expense.amount / member_count).quantize(CURRENCY_UNIT, rounding=ROUND_HALF_UP)
        splits_to_create = [
            ExpenseSplit(expense=expense, user=member, amount_owed=share)
            for member in members
        ]
        if splits_to_create:
            remainder = expense.amount - sum(s.amount_owed for s in splits_to_create)
            if remainder:
                splits_to_create[0].amount_owed += remainder

    elif expense.split_type == 'EXACT':
        total = sum(Decimal(str(d['amount'])) for d in split_data)
        if abs(total - expense.amount) > Decimal('0.05'):
            raise ValueError(
                f"EXACT split amounts ({total}) do not match expense total ({expense.amount})."
            )
        splits_to_create = [
            ExpenseSplit(
                expense=expense,
                user_id=d['user'],
                amount_owed=Decimal(str(d['amount'])).quantize(CURRENCY_UNIT),
            )
            for d in split_data
        ]

    elif expense.split_type == 'PERCENT':
        total_pct = sum(Decimal(str(d['percentage'])) for d in split_data)
        if abs(total_pct - Decimal('100')) > Decimal('0.05'):
            raise ValueError(f"Percentages sum to {total_pct}, not 100.")
        splits_to_create = [
            ExpenseSplit(
                expense=expense,
                user_id=d['user'],
                amount_owed=(
                    (Decimal(str(d['percentage'])) / 100) * expense.amount
                ).quantize(CURRENCY_UNIT, rounding=ROUND_HALF_UP),
            )
            for d in split_data
        ]
        if splits_to_create:
            remainder = expense.amount - sum(s.amount_owed for s in splits_to_create)
            if remainder:
                splits_to_create[0].amount_owed += remainder

    elif expense.split_type == 'ITEM':
        for d in split_data:
            item = ExpenseItem.objects.create(
                expense=expense,
                name=d['name'],
                amount=Decimal(str(d['amount'])),
            )
            share = (item.amount / len(d['user_ids'])).quantize(CURRENCY_UNIT, rounding=ROUND_HALF_UP)
            item_splits = [
                ExpenseSplit(expense=expense, item=item, user_id=uid, amount_owed=share)
                for uid in d['user_ids']
            ]
            if item_splits:
                remainder = item.amount - sum(s.amount_owed for s in item_splits)
                if remainder:
                    item_splits[0].amount_owed += remainder
            splits_to_create.extend(item_splits)

    if splits_to_create:
        ExpenseSplit.objects.bulk_create(splits_to_create)


# ── Settlement confirmation ───────────────────────────────────────────────────

@transaction.atomic
def confirm_settlement(settlement: Settlement, confirmed_by: User) -> dict:
    """
    Confirm a settlement. Three atomic writes:
      1. Settlement status → CONFIRMED
      2. Payer reliability score += 0.5 (clamped to 100 via F() expression)
      3. ReliabilityHistory record created

    Guards:
      - Only the receiver can confirm.
      - Double-confirmation blocked via select_for_update row lock.
      - Over-settlement blocked — amount cannot exceed actual pairwise debt.
    """
    # Lock the row — prevents concurrent confirms on the same settlement
    settlement = Settlement.objects.select_for_update().get(pk=settlement.pk)

    if settlement.receiver != confirmed_by:
        raise PermissionError("Only the receiver can confirm this settlement.")

    if settlement.status == 'CONFIRMED':
        raise ValueError("This settlement has already been confirmed.")

    # Prevent over-settlement race condition: balances might have changed since this PENDING
    # settlement was created. If the amount now exceeds the actual debt, block confirmation.
    actual_debt = _compute_pairwise_debt(
        group_id=settlement.group_id,
        payer_id=settlement.payer_id,
        receiver_id=settlement.receiver_id
    )
    if settlement.amount > actual_debt + Decimal('0.05'):
        raise ValueError(
            f"Over-settlement detected. Due to recent changes, the payer now only owes "
            f"{actual_debt}. This {settlement.amount} settlement can no longer be confirmed."
        )


    # Write 1 — settlement status
    # The post_save signal on Settlement will automatically call
    # users/services.increment_reliability_score() via expenses/signals.py,
    # which safely clamps the score at 100 via DB-level Least().
    settlement.status = 'CONFIRMED'
    settlement.save(update_fields=['status', 'updated_at'])

    # Re-read payer to return the DB-computed score (signal may have updated it).
    payer = User.objects.get(pk=settlement.payer_id)

    return {
        'status':                'confirmed',
        'new_reliability_score': payer.reliability_score,
    }


def _compute_pairwise_debt(group_id: int, payer_id: int, receiver_id: int) -> Decimal:
    """
    Compute how much payer_id actually owes receiver_id in this group.
    Used only by confirm_settlement for the over-settlement guard.

    Returns Decimal('0') if no debt exists or the debt direction is reversed.
    """
    from .utils import compute_group_balances

    balances    = compute_group_balances(group_id)
    balance_map = {b['user_id']: b['net_balance'] for b in balances}

    payer_balance    = balance_map.get(payer_id,    Decimal('0'))
    receiver_balance = balance_map.get(receiver_id, Decimal('0'))

    # Valid debt: payer is a debtor (negative), receiver is a creditor (positive)
    if payer_balance >= 0 or receiver_balance <= 0:
        return Decimal('0')

    return min(abs(payer_balance), receiver_balance).quantize(Decimal('0.01'))


# ── Delete guard ──────────────────────────────────────────────────────────────

def get_blocking_settlements(expense: Expense) -> list[dict]:
    """
    Return confirmed settlements that would be invalidated by deleting this expense.
    Used in both the can-delete check endpoint and destroy().

    Returns an empty list if deletion is safe.
    Single query — no N+1 regardless of split count.
    """
    blocking = Settlement.objects.filter(
        group=expense.group,
        payer__in=expense.splits.values('user'),
        receiver=expense.paid_by,
        status='CONFIRMED',
        is_active=True,
        created_at__gte=expense.created_at,
    ).select_related('payer', 'receiver')

    return [
        {'debtor': s.payer.username, 'creditor': s.receiver.username}
        for s in blocking
    ]