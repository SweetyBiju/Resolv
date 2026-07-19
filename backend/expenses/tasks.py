"""
expenses/tasks.py
─────────────────
Celery async tasks for the expenses app.

recompute_group_balances — triggered after any expense or settlement mutation.
Computes raw balances + simplified settlements and caches both for 5 minutes.
The balance endpoint reads from cache first; this task keeps the cache warm.
"""

import logging

from celery import shared_task
from django.core.cache import cache

logger        = logging.getLogger('resolv.tasks')
CACHE_TTL     = 300                         # 5 minutes
CACHE_KEY     = 'group_balances_{group_id}'


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def recompute_group_balances(self, group_id: int):
    """
    Recompute and cache balances for a group.

    Retries up to 3 times with a 5-second delay on failure.
    On success, cache holds both raw balances and simplified settlements
    so the balance endpoint never blocks on computation in the request cycle.
    """
    try:
        from .utils import compute_group_balances, simplify_debts

        raw        = compute_group_balances(group_id)
        simplified = simplify_debts(raw)

        cache.set(
            CACHE_KEY.format(group_id=group_id),
            {'raw': raw, 'simplified': simplified},
            timeout=CACHE_TTL,
        )

        logger.info(
            "Balances recomputed for group %d — %d settlement(s) suggested.",
            group_id, len(simplified),
        )

    except Exception as exc:
        logger.error(
            "Balance recomputation failed for group %d: %s", group_id, exc
        )
        raise self.retry(exc=exc)