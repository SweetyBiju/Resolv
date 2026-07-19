"""
expenses/views.py
─────────────────
Two ViewSets, one domain.

ExpenseViewSet    — CRUD for expenses + balance + suggested settlements + can-delete
SettlementViewSet — CRUD for settlements + confirm action

Design rules followed:
  - Views handle HTTP only. All business logic is in services.py.
  - get_serializer_class() routes read vs write serializers cleanly.
  - split_data comes from serializer.validated_data, not request.data raw.
  - Queryset is scoped to group membership — simple, single JOIN, no distinct needed.
  - Cache is read-first on balance endpoints; Celery keeps it warm after mutations.
"""

import datetime
import logging

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Expense, Settlement
from .permissions import IsPayerOrGroupAdmin
from .serializers import (
    ExpenseSerializer,
    ExpenseWriteSerializer,
    SettlementSerializer,
    SettlementWriteSerializer,
)
from .services import (
    confirm_settlement,
    create_expense_with_splits,
    get_blocking_settlements,
    update_expense_with_splits,
)
from .tasks import recompute_group_balances
from .utils import compute_group_balances, simplify_debts

logger    = logging.getLogger('resolv.views')
CACHE_KEY = 'group_balances_{group_id}'


# ── Expense ViewSet ───────────────────────────────────────────────────────────

class ExpenseViewSet(viewsets.ModelViewSet):
    """
    list:    GET  /api/v1/expenses/
    create:  POST /api/v1/expenses/
    retrieve:GET  /api/v1/expenses/{id}/
    update:  PATCH /api/v1/expenses/{id}/
    destroy: DELETE /api/v1/expenses/{id}/

    Extra actions:
      GET /api/v1/expenses/balances/{group_id}/
      GET /api/v1/expenses/suggested-settlements/{group_id}/
      GET /api/v1/expenses/{id}/can-delete/
    """

    permission_classes = [IsAuthenticated, IsPayerOrGroupAdmin]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ExpenseWriteSerializer
        return ExpenseSerializer

    def get_queryset(self):
        """
        Return active expenses in groups the requesting user belongs to.
        Supports optional query-param filters:
          ?group=<id>  ?category=<CAT>  ?date_after=YYYY-MM-DD  ?date_before=YYYY-MM-DD
        Single JOIN on group__members — no OR conditions, no distinct() needed.
        prefetch_related loads splits + items in 2 extra queries (not N queries).
        """
        qs = (
            Expense.objects
            .filter(group__members=self.request.user, group__is_active=True)
            .select_related('paid_by', 'group')
            .prefetch_related('splits__user', 'items')
            .order_by('-date', '-created_at')
        )

        params = self.request.query_params
        group_id    = params.get('group')
        category    = params.get('category')
        date_after  = params.get('date_after')
        date_before = params.get('date_before')

        if group_id:
            qs = qs.filter(group_id=group_id)
        if category:
            qs = qs.filter(category=category.upper())
        if date_after:
            qs = qs.filter(date__gte=date_after)
        if date_before:
            qs = qs.filter(date__lte=date_before)

        return qs

    def perform_create(self, serializer):
        """
        Validate payer membership, then delegate to service layer.
        split_data comes from serializer.validated_data — already validated.
        """
        group      = serializer.validated_data['group']
        split_data = serializer.validated_data.pop('split_data', [])

        # Resolve payer: explicit paid_by in payload, else request.user
        # BUG 6 FIX: single .get() call instead of .exists() then .get() (was 2 DB queries).
        # Also validates paid_by_id is a valid integer before touching the DB.
        paid_by_id = self.request.data.get('paid_by')
        if paid_by_id:
            try:
                paid_by = group.members.get(pk=int(paid_by_id))
            except (ValueError, TypeError):
                raise ValidationError({"paid_by": "paid_by must be a valid user ID (integer)."})
            except group.members.model.DoesNotExist:
                raise ValidationError({"paid_by": "The specified payer is not a member of this group."})
        else:
            paid_by = self.request.user

        create_expense_with_splits(
            title      = serializer.validated_data['title'],
            amount     = serializer.validated_data['amount'],
            group      = group,
            paid_by    = paid_by,
            split_type = serializer.validated_data.get('split_type', 'EQUAL'),
            split_data = split_data,
            currency   = serializer.validated_data.get('currency', 'INR'),
            category   = serializer.validated_data.get('category', 'OTHER'),
            notes      = serializer.validated_data.get('notes', ''),
            receipt_url= serializer.validated_data.get('receipt_url'),
            date       = serializer.validated_data.get('date'),
        )
        recompute_group_balances.delay(group.id)

    def perform_update(self, serializer):
        """
        Replace expense fields and all splits atomically via service.
        split_data comes from serializer.validated_data — already validated.
        """
        split_data = serializer.validated_data.pop('split_data', [])
        expense    = update_expense_with_splits(
            expense        = serializer.instance,
            validated_data = serializer.validated_data,
            split_data     = split_data,
        )
        recompute_group_balances.delay(expense.group_id)

    def destroy(self, request, *args, **kwargs):
        """Soft delete — blocked if confirmed settlements exist against this expense."""
        expense  = self.get_object()
        blocking = get_blocking_settlements(expense)
        if blocking:
            return Response(
                {"detail": "SETTLED_DEBTS_EXIST", "blocking": blocking},
                status=status.HTTP_400_BAD_REQUEST,
            )
        expense.delete()
        recompute_group_balances.delay(expense.group_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Extra actions ─────────────────────────────────────────────────────────

    @action(detail=True, methods=['get'], url_path='can-delete')
    def can_delete_check(self, request, pk=None):
        """Pre-flight check before the user attempts deletion."""
        expense  = self.get_object()
        blocking = get_blocking_settlements(expense)
        if blocking:
            return Response(
                {"can_delete": False, "reason": "SETTLED_DEBTS_EXIST", "blocking": blocking},
                status=status.HTTP_200_OK,
            )
        return Response({"can_delete": True}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'],
            url_path=r'balances/(?P<group_id>[^/.]+)')
    def group_balances(self, request, group_id=None):
        """
        Return net balance per member for a group.
        Reads from cache if warm; computes from DB otherwise.
        """
        group_id = int(group_id)
        if not _user_in_group(request.user, group_id):
            return Response({"error": "Not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

        cached = cache.get(CACHE_KEY.format(group_id=group_id))
        if cached:
            return Response(cached['raw'])

        balances = compute_group_balances(group_id)
        return Response(balances)

    @action(detail=False, methods=['get'],
            url_path=r'suggested-settlements/(?P<group_id>[^/.]+)')
    def suggested_settlements(self, request, group_id=None):
        """
        Return simplified settlement suggestions for a group.
        Uses cached result if available; falls back to live computation.
        """
        group_id = int(group_id)
        if not _user_in_group(request.user, group_id):
            return Response({"error": "Not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

        cached = cache.get(CACHE_KEY.format(group_id=group_id))
        if cached:
            return Response({"group_id": group_id, "suggested_payments": cached['simplified']})

        balances   = compute_group_balances(group_id)
        simplified = simplify_debts(balances)
        return Response({"group_id": group_id, "suggested_payments": simplified})


# ── Settlement ViewSet ────────────────────────────────────────────────────────

class SettlementViewSet(viewsets.ModelViewSet):
    """
    list:    GET  /api/v1/settlements/
    create:  POST /api/v1/settlements/
    retrieve:GET  /api/v1/settlements/{id}/
    destroy: DELETE /api/v1/settlements/{id}/   (soft delete → CANCELLED)

    Extra actions:
      POST /api/v1/settlements/{id}/confirm_settlement/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return SettlementWriteSerializer
        return SettlementSerializer

    def get_queryset(self):
        """
        Return settlements where the user is payer or receiver.
        Uses all_objects to include soft-deleted (CANCELLED) settlements.
        Supports optional query-param filter:
          ?status=PENDING | CONFIRMED | CANCELLED
        Users see settlements they initiated AND received.
        """
        user = self.request.user
        qs = (
            Settlement.all_objects
            .filter(group__members=user, group__is_active=True)
            .select_related('payer', 'receiver', 'group')
            .order_by('-created_at')
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        return qs

    def perform_create(self, serializer):
        """
        Create a settlement. Guards:
          - Duplicate detection: same payer/receiver/amount within 60 seconds.
          - payer is always request.user — never from payload.
        """
        receiver = serializer.validated_data['receiver']
        amount   = serializer.validated_data['amount']

        # Duplicate guard — prevents accidental double-submission
        cutoff = timezone.now() - datetime.timedelta(seconds=60)
        if Settlement.objects.filter(
            payer=self.request.user,
            receiver=receiver,
            amount=amount,
            created_at__gte=cutoff,
            is_active=True,
        ).exists():
            raise ValidationError(
                {"detail": "Duplicate settlement detected. Please wait 60 seconds before retrying."}
            )

        serializer.save(payer=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete a settlement — only PENDING settlements can be cancelled.
        CONFIRMED settlements cannot be undone.
        """
        settlement = self.get_object()

        if settlement.payer != request.user:
            return Response(
                {"error": "Only the payer can cancel a settlement."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if settlement.status == 'CONFIRMED':
            return Response(
                {"error": "Confirmed settlements cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        settlement.delete()     # soft delete → is_active=False, status=CANCELLED
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='confirm_settlement')
    def confirm_settlement_action(self, request, pk=None):
        """Receiver confirms payment. Atomic: status + score + history."""
        settlement = self.get_object()
        try:
            result = confirm_settlement(settlement, confirmed_by=request.user)
            recompute_group_balances.delay(settlement.group_id)
            return Response(result, status=status.HTTP_200_OK)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ── Private helpers ───────────────────────────────────────────────────────────

def _user_in_group(user, group_id: int) -> bool:
    """Single query membership check. Used by balance endpoints."""
    from groups.models import Group
    return Group.objects.filter(pk=group_id, members=user).exists()