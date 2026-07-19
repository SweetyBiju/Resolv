"""
Resolv Debt Simplification Engine
──────────────────────────────────
Core algorithm: O(n log n) Greedy Heap-Based Settlement Minimization.
Guarantees the minimum number of transactions for any debt graph.
"""

import heapq
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import TypedDict

from django.db.models import Sum

logger = logging.getLogger('resolv.algorithm')

# ── Constants ────────────────────────────────────────────────────────────────
EPSILON       = Decimal('0.005')   # Half a paisa — balances below this are treated as settled
CURRENCY_UNIT = Decimal('0.01')    # Smallest representable currency unit


# ── Type contracts ────────────────────────────────────────────────────────────
class BalanceEntry(TypedDict):
    user_id:     int
    username:    str
    total_paid:  Decimal
    total_owed:  Decimal
    net_balance: Decimal


class SettlementSuggestion(TypedDict):
    from_user:    str
    from_user_id: int
    to_user:      str
    to_user_id:   int
    amount:       Decimal   # Always Decimal, NEVER float


# ── Balance Computation  ─────────────────────────
def compute_group_balances(group_id: int) -> list[BalanceEntry]:
    """
    Compute net balance for every member of a group.

    net_balance = total_paid - total_owed + total_sent_settled - total_received_settled
    Positive → creditor (others owe them)
    Negative → debtor   (they owe others)

    Confirmed settlements reduce outstanding debt: when a payer settles with a
    receiver, the payer's net goes up (less debt) and the receiver's net goes
    down (less credit). Without this, confirming a settlement has zero effect
    on the displayed balances.

    Uses 5 DB queries regardless of group size (no N+1).
    """
    from expenses.models import Expense, ExpenseSplit, Settlement
    from groups.models import GroupMembership

    # Query 1: all group members so every member appears in output
    member_qs = (
        GroupMembership.objects
        .filter(group_id=group_id)
        .select_related('user')
    )
    members = {m.user_id: m.user.username for m in member_qs}

    # Query 2: total paid per user
    paid_qs = (
        Expense.objects
        .filter(group_id=group_id, is_active=True)
        .values('paid_by', 'paid_by__username')
        .annotate(total_paid=Sum('amount'))
    )
    paid_map = {
        row['paid_by']: (row['paid_by__username'], row['total_paid'])
        for row in paid_qs
    }

    # Query 3: total owed per user (from their ExpenseSplit records)
    owed_qs = (
        ExpenseSplit.objects
        .filter(expense__group_id=group_id, expense__is_active=True)
        .values('user', 'user__username')
        .annotate(total_owed=Sum('amount_owed'))
    )
    owed_map = {
        row['user']: (row['user__username'], row['total_owed'])
        for row in owed_qs
    }

    # Query 4: confirmed settlements sent (payer side) — reduces debt
    sent_qs = (
        Settlement.objects
        .filter(group_id=group_id, status='CONFIRMED', is_active=True)
        .values('payer')
        .annotate(total_sent=Sum('amount'))
    )
    sent_map = {row['payer']: row['total_sent'] for row in sent_qs}

    # Query 5: confirmed settlements received (receiver side) — reduces credit
    received_qs = (
        Settlement.objects
        .filter(group_id=group_id, status='CONFIRMED', is_active=True)
        .values('receiver')
        .annotate(total_received=Sum('amount'))
    )
    received_map = {row['receiver']: row['total_received'] for row in received_qs}

    # Union: all member IDs in the group + anyone who touched an expense/settlement
    all_user_ids = (
        set(members)
        | set(paid_map)
        | set(owed_map)
        | set(sent_map)
        | set(received_map)
    )

    balances: list[BalanceEntry] = []
    for uid in all_user_ids:
        username = (
            members.get(uid)
            or (paid_map.get(uid) or (None,))[0]
            or (owed_map.get(uid) or (None,))[0]
            or f'User {uid}'
        )
        paid     = (paid_map.get(uid)     or (None, Decimal('0.00')))[1] or Decimal('0.00')
        owed     = (owed_map.get(uid)     or (None, Decimal('0.00')))[1] or Decimal('0.00')
        sent     = sent_map.get(uid,     Decimal('0.00')) or Decimal('0.00')
        received = received_map.get(uid, Decimal('0.00')) or Decimal('0.00')
        balances.append({
            'user_id':     uid,
            'username':    username,
            'total_paid':  paid,
            'total_owed':  owed,
            'net_balance': paid - owed + sent - received,
        })

    return balances


# ── Core Algorithm ────────────────────────────────────────────────────────────
def simplify_debts(balances_list: list[BalanceEntry]) -> list[SettlementSuggestion]:
    """
    Greedy Heap-Based Debt Simplification.

    Complexity:  O(n log n) time  |  O(n) space
    Optimality:  Produces the minimum possible number of transactions.
    Proof:       Each transaction fully resolves at least one participant.
                 n participants → at most n-1 transactions.

    Args:
        balances_list: Output of compute_group_balances(). All net_balance
                       values must be Decimal and must sum to zero.

    Returns:
        Ordered list of settlement suggestions. Amounts are always Decimal.

    Raises:
        ValueError:  Input balances don't sum to zero (upstream data corruption).
        RuntimeError: Algorithm terminated with unresolved balances (should never
                      happen if ValueError check passes — indicates a logic bug).
    """
    if not balances_list:
        return []

    # ── Input normalisation ───────────────────────────────────────────────────
    normalized: list[BalanceEntry] = []
    for item in balances_list:
        bal = item['net_balance']
        if not isinstance(bal, Decimal):
            bal = Decimal(str(bal))
        normalized.append({**item, 'net_balance': bal})

    # ── GUARD: Zero-sum invariant  ───────────────────────────────
    total = sum(item['net_balance'] for item in normalized)
    if abs(total) > EPSILON:
        logger.error(
            "simplify_debts received non-zero-sum balances for input %s (total=%s). "
            "This indicates corrupted ExpenseSplit data.",
            [i.get('username') or i.get('user', 'Unknown') for i in normalized], total
        )
        raise ValueError(
            f"Group balances are not zero-sum (residual={total}). "
            "Expense splits may be corrupted. Cannot generate settlements."
        )

    # ── Build heaps ───────────────────────────────────────────────────────────
    # debt_heap: min-heap on balance value (most negative = highest priority)
    # cred_heap: max-heap via negation (most positive = highest priority)
    debt_heap: list[tuple[Decimal, str, int]] = []
    cred_heap: list[tuple[Decimal, str, int]] = []

    for item in normalized:
        bal  = item['net_balance']
        name = item['username']
        uid  = item['user_id']
        if bal < -EPSILON:
            heapq.heappush(debt_heap, (bal, name, uid))
        elif bal > EPSILON:
            heapq.heappush(cred_heap, (-bal, name, uid))

    settlements: list[SettlementSuggestion] = []

    # ── Greedy settlement loop ────────────────────────────────────────────────
    while debt_heap and cred_heap:
        d_bal,  d_name, d_uid = heapq.heappop(debt_heap)
        nc_bal, c_name, c_uid = heapq.heappop(cred_heap)
        c_bal = -nc_bal

        settle_amount = min(abs(d_bal), c_bal).quantize(
            CURRENCY_UNIT, rounding=ROUND_HALF_UP
        )

        settlements.append(SettlementSuggestion(
            from_user=d_name,       
            from_user_id=d_uid,
            to_user=c_name,
            to_user_id=c_uid,
            amount=settle_amount,
        ))

        remaining_debt   = (d_bal  + settle_amount).quantize(CURRENCY_UNIT)
        remaining_credit = (c_bal  - settle_amount).quantize(CURRENCY_UNIT)

        if remaining_debt < -EPSILON:
            heapq.heappush(debt_heap, (remaining_debt, d_name, d_uid))
        if remaining_credit > EPSILON:
            heapq.heappush(cred_heap, (-remaining_credit, c_name, c_uid))

    # ── GUARD ───────────────────────────────
    if debt_heap or cred_heap:
        leftover = (
            [f"{n}({b})" for b, n, _ in debt_heap] +
            [f"{n}({-b})" for b, n, _ in cred_heap]
        )
        raise RuntimeError(
            f"Settlement loop terminated with unresolved balances: {leftover}. "
            "The zero-sum guard should have caught this — file a bug report."
        )

    logger.info(
        "simplify_debts: resolved %d participants into %d transactions.",
        len([i for i in normalized if abs(i['net_balance']) > EPSILON]),
        len(settlements),
    )
    return settlements


# ── Balance Journey ───────────────────────────────────────────────────────────
def get_balance_journey(group_id: int, user_id: int) -> list[dict]:
    """
    Computes a chronological ledger of a user's balance changes in a group.
    
    Event types:
      - EXPENSE_PAID: User paid for an expense (+)
      - EXPENSE_SPLIT: User's share of an expense (-)
      - SETTLEMENT_SENT: User paid someone else (+)
      - SETTLEMENT_RECEIVED: User received money (-)
      
    Returns list of dicts with date, type, title, change, running_balance.
    """
    from expenses.models import Expense, ExpenseSplit, Settlement
    from itertools import chain

    # 1. Expenses paid by the user
    paid_qs = Expense.objects.filter(
        group_id=group_id, paid_by_id=user_id, is_active=True
    ).values('id', 'created_at', 'title', 'amount')
    
    # 2. Expense splits owed by the user
    split_qs = ExpenseSplit.objects.filter(
        expense__group_id=group_id, user_id=user_id, expense__is_active=True
    ).values('expense_id', 'expense__created_at', 'expense__title', 'amount_owed')
    
    # 3. Settlements sent by the user (status='CONFIRMED')
    sent_qs = Settlement.objects.filter(
        group_id=group_id, payer_id=user_id, status='CONFIRMED', is_active=True
    ).values('id', 'created_at', 'receiver__username', 'amount')
    
    # 4. Settlements received by the user
    received_qs = Settlement.objects.filter(
        group_id=group_id, receiver_id=user_id, status='CONFIRMED', is_active=True
    ).values('id', 'created_at', 'payer__username', 'amount')

    events = []
    
    for row in paid_qs:
        events.append({
            'timestamp': row['created_at'],
            'type': 'EXPENSE_PAID',
            'title': row['title'],
            'change': Decimal(str(row['amount'])),
            'ref_id': row['id'],
        })
        
    for row in split_qs:
        events.append({
            'timestamp': row['expense__created_at'],
            'type': 'EXPENSE_SPLIT',
            'title': row['expense__title'],
            'change': -Decimal(str(row['amount_owed'])),
            'ref_id': row['expense_id'],
        })
        
    for row in sent_qs:
        events.append({
            'timestamp': row['created_at'],
            'type': 'SETTLEMENT_SENT',
            'title': f"Paid {row['receiver__username']}",
            'change': Decimal(str(row['amount'])),
            'ref_id': row['id'],
        })
        
    for row in received_qs:
        events.append({
            'timestamp': row['created_at'],
            'type': 'SETTLEMENT_RECEIVED',
            'title': f"Received from {row['payer__username']}",
            'change': -Decimal(str(row['amount'])),
            'ref_id': row['id'],
        })
        
    # Sort chronologically
    events.sort(key=lambda x: x['timestamp'])
    
    journey = []
    running_balance = Decimal('0.00')
    
    for ev in events:
        running_balance += ev['change']
        journey.append({
            'date': ev['timestamp'].isoformat(),
            'event_type': ev['type'],
            'title': ev['title'],
            'balance_change': str(ev['change']),
            'running_balance': str(running_balance),
        })
        
    return journey