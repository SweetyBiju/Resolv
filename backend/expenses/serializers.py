"""
expenses/serializers.py
───────────────────────
Serializer design rules:
  - Read serializers (used in GET responses) are flat and human-readable.
  - Write serializers (used in POST/PATCH) validate input and carry split_data.
  - split_data is validated here so services.py receives clean, trusted input.
  - No business logic lives here — validation only.
"""

from decimal import Decimal

from rest_framework import serializers

from .models import Expense, ExpenseItem, ExpenseSplit, Settlement

SPLIT_TOLERANCE = Decimal('0.05')   # max allowable rounding gap across all splits


# ── Sub-serializers (read only) ───────────────────────────────────────────────

class ExpenseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExpenseItem
        fields = ['id', 'name', 'amount']


class ExpenseSplitSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model  = ExpenseSplit
        fields = ['id', 'user', 'username', 'amount_owed']


# ── Expense read serializer ───────────────────────────────────────────────────

class ExpenseSerializer(serializers.ModelSerializer):
    """
    Used for GET responses only.
    Nests splits and items inline for a complete picture in one call.
    """
    splits           = ExpenseSplitSerializer(many=True, read_only=True)
    items            = ExpenseItemSerializer(many=True, read_only=True)
    paid_by_username = serializers.ReadOnlyField(source='paid_by.username')
    group_name       = serializers.ReadOnlyField(source='group.name')

    class Meta:
        model  = Expense
        fields = [
            'id', 'title', 'amount', 'currency', 'category',
            'notes', 'receipt_url', 'date',
            'paid_by', 'paid_by_username',
            'group', 'group_name',
            'split_type', 'splits', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields   # entire serializer is read-only


# ── Split input serializers (write only, nested inside ExpenseWriteSerializer) ─

class EqualSplitInputSerializer(serializers.Serializer):
    """EQUAL splits have no extra input — members are derived from group."""
    pass


class ExactSplitInputSerializer(serializers.Serializer):
    user   = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))


class PercentSplitInputSerializer(serializers.Serializer):
    user       = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0.01'))


class ItemSplitInputSerializer(serializers.Serializer):
    name     = serializers.CharField(max_length=255)
    amount   = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )


# ── Expense write serializer ──────────────────────────────────────────────────

class ExpenseWriteSerializer(serializers.ModelSerializer):
    """
    Used for POST (create) and PATCH (update).
    Validates core fields + split_data according to split_type.
    split_data is passed through to services.py after validation.
    """
    split_data = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        write_only=True,
    )

    class Meta:
        model  = Expense
        fields = [
            'title', 'amount', 'currency', 'category',
            'notes', 'receipt_url', 'date',
            'group', 'split_type', 'split_data',
        ]

    # ── Field-level validation ─────────────────────────────────────────────────

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Expense amount must be positive.")
        return value

    def validate_currency(self, value):
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError(
                "Currency must be a valid 3-letter ISO 4217 code (e.g. INR, USD)."
            )
        return value.upper()

    # ── Object-level validation ────────────────────────────────────────────────

    def validate(self, data):
        self._validate_split_data(data)
        return data

    def _validate_split_data(self, data):
        split_type = data.get('split_type', 'EQUAL')
        split_data = data.get('split_data', [])
        amount     = data.get('amount', Decimal('0'))
        group      = data.get('group')

        if split_type == 'EQUAL':
            # No split_data needed — members derived from group in service
            return

        # Fetch valid member IDs to prevent assigning debt to arbitrary users
        valid_member_ids = set(group.members.values_list('id', flat=True)) if group else set()

        if split_type == 'EXACT':
            if not split_data:
                raise serializers.ValidationError(
                    {"split_data": "EXACT split requires per-user amount entries."}
                )
            validated_splits = []
            for entry in split_data:
                s = ExactSplitInputSerializer(data=entry)
                if not s.is_valid():
                    raise serializers.ValidationError({"split_data": s.errors})
                if s.validated_data['user'] not in valid_member_ids:
                    raise serializers.ValidationError(
                        {"split_data": f"User {s.validated_data['user']} is not a member of this group."}
                    )
                validated_splits.append(s.validated_data)
            data['split_data'] = validated_splits
            
            total = sum(e['amount'] for e in validated_splits)
            if abs(total - amount) > SPLIT_TOLERANCE:
                raise serializers.ValidationError(
                    {"split_data": f"EXACT amounts sum to {total}, expected {amount}."}
                )

        elif split_type == 'PERCENT':
            if not split_data:
                raise serializers.ValidationError(
                    {"split_data": "PERCENT split requires per-user percentage entries."}
                )
            validated_splits = []
            for entry in split_data:
                s = PercentSplitInputSerializer(data=entry)
                if not s.is_valid():
                    raise serializers.ValidationError({"split_data": s.errors})
                if s.validated_data['user'] not in valid_member_ids:
                    raise serializers.ValidationError(
                        {"split_data": f"User {s.validated_data['user']} is not a member of this group."}
                    )
                validated_splits.append(s.validated_data)
            data['split_data'] = validated_splits

            total_pct = sum(e['percentage'] for e in validated_splits)
            if abs(total_pct - Decimal('100')) > SPLIT_TOLERANCE:
                raise serializers.ValidationError(
                    {"split_data": f"Percentages sum to {total_pct}, must equal 100."}
                )

        elif split_type == 'ITEM':
            if not split_data:
                raise serializers.ValidationError(
                    {"split_data": "ITEM split requires at least one item entry."}
                )
            validated_splits = []
            for entry in split_data:
                s = ItemSplitInputSerializer(data=entry)
                if not s.is_valid():
                    raise serializers.ValidationError({"split_data": s.errors})
                for uid in s.validated_data['user_ids']:
                    if uid not in valid_member_ids:
                        raise serializers.ValidationError(
                            {"split_data": f"User {uid} is not a member of this group."}
                        )
                validated_splits.append(s.validated_data)
            data['split_data'] = validated_splits

            total_items = sum(e['amount'] for e in validated_splits)
            if abs(total_items - amount) > SPLIT_TOLERANCE:
                raise serializers.ValidationError(
                    {"split_data": f"Item amounts sum to {total_items}, expected {amount}."}
                )


# ── Settlement serializers ────────────────────────────────────────────────────

class SettlementSerializer(serializers.ModelSerializer):
    """Read serializer — used in GET responses."""
    payer_username    = serializers.ReadOnlyField(source='payer.username')
    receiver_username = serializers.ReadOnlyField(source='receiver.username')
    group_name        = serializers.ReadOnlyField(source='group.name')

    class Meta:
        model  = Settlement
        fields = [
            'id', 'group', 'group_name',
            'payer', 'payer_username',
            'receiver', 'receiver_username',
            'amount', 'currency',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class SettlementWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer — used for POST (create settlement).
    payer is always set from request.user in the view, never from input.
    status is always PENDING on creation.
    """

    allow_over_settlement = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model  = Settlement
        fields = ['group', 'receiver', 'amount', 'currency', 'allow_over_settlement']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Settlement amount must be positive.")
        return value

    def validate_currency(self, value):
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError(
                "Currency must be a valid 3-letter ISO 4217 code (e.g. INR, USD)."
            )
        return value.upper()

    def validate(self, data):
        request  = self.context.get('request')
        group    = data.get('group')
        receiver = data.get('receiver')
        amount   = data.get('amount', Decimal('0'))
        allow_over = data.pop('allow_over_settlement', False)

        # Self-settlement block — friendly error before DB constraint fires
        if request and receiver and request.user.id == receiver.id:
            raise serializers.ValidationError(
                {"receiver": "You cannot settle a debt with yourself."}
            )

        # Receiver must be a member of the group
        if group and receiver:
            if not group.members.filter(pk=receiver.pk).exists():
                raise serializers.ValidationError(
                    {"receiver": "The receiver is not a member of this group."}
                )

        # Pairwise debt guard — block zero-debt and over-settlement at creation time
        # Skipped when user explicitly acknowledges over-settlement (lending money)
        if request and group and receiver and not allow_over:
            from .utils import compute_group_balances
            balances    = compute_group_balances(group.id)
            balance_map = {b['user_id']: b['net_balance'] for b in balances}

            payer_balance    = balance_map.get(request.user.id, Decimal('0'))
            receiver_balance = balance_map.get(receiver.id,      Decimal('0'))

            # Valid debt: payer is a debtor (negative net), receiver is a creditor (positive net)
            if payer_balance >= 0 or receiver_balance <= 0:
                raise serializers.ValidationError(
                    {"amount": f"You do not owe {receiver.username} any debt in this group."}
                )

            actual_debt = min(abs(payer_balance), receiver_balance).quantize(Decimal('0.01'))
            if amount > actual_debt + Decimal('0.05'):
                raise serializers.ValidationError(
                    {"amount": (
                        f"Settlement amount ({amount}) exceeds your actual debt of "
                        f"{actual_debt} to {receiver.username}."
                    )}
                )

        return data