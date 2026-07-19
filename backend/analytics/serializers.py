from rest_framework import serializers
from .models import Budget

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Budget
        fields = [
            'id', 'user', 'group', 'category',
            'amount_limit', 'month', 'year', 'alert_thresholds_sent'
        ]
        read_only_fields = ['user', 'alert_thresholds_sent']

    def validate(self, data):
        amount = data.get('amount_limit')
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount_limit": "Amount must be greater than 0."})
            
        month = data.get('month')
        if month is not None and not (1 <= month <= 12):
            raise serializers.ValidationError({"month": "Month must be between 1 and 12."})
            
        year = data.get('year')
        if year is not None and not (2000 <= year <= 2100):
            raise serializers.ValidationError({"year": "Year must be reasonable (2000-2100)."})
            
        # Group membership check is usually done in the view or services,
        # but we can do a simple check if group is provided.
        group = data.get('group')
        user = self.context['request'].user if 'request' in self.context else None
        
        if group and user and not group.members.filter(id=user.id).exists():
            raise serializers.ValidationError({"group": "You must be a member of this group."})
            
        return data

class MonthlyTrendSerializer(serializers.Serializer):
    month = serializers.CharField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)

class CategoryBreakdownSerializer(serializers.Serializer):
    category = serializers.CharField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)

class BudgetVsActualSerializer(serializers.Serializer):
    category = serializers.CharField()
    budget_limit = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    actual_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    percentage_used = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    over_budget = serializers.BooleanField(allow_null=True)
    budget_id = serializers.IntegerField(allow_null=True, required=False)

class SpendingInsightSerializer(serializers.Serializer):
    type = serializers.CharField()
    message = serializers.CharField()
    severity = serializers.CharField()
