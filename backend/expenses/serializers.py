from rest_framework import serializers
from decimal import Decimal
from .models import Expense, ExpenseSplit, ExpenseItem

class ExpenseSplitSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = ExpenseSplit
        fields = ['user', 'username', 'amount_owed']

class ExpenseSerializer(serializers.ModelSerializer):
    splits = ExpenseSplitSerializer(many=True, read_only=True)
    paid_by_username = serializers.ReadOnlyField(source='paid_by.username')

    class Meta:
        model = Expense
        fields = [
            'id', 'title', 'amount', 'currency', 'paid_by', 
            'paid_by_username', 'group', 'trip', 'split_type', 
            'splits', 'date'
        ]
        # Automate paid_by so the user doesn't have to provide it manually
        read_only_fields = ['paid_by']



    def validate(self, data):
        """
        Ensures that EXACT and PERCENT splits add up to the total expense amount.
       
        """
        split_type = data.get('split_type')
        amount = Decimal(str(data.get('amount', 0)))
        
        # Access split_data from the request context
        request = self.context.get('request')
        split_data = request.data.get('split_data', []) if request else []

        if split_type == 'EXACT':
            total_split_amount = sum(Decimal(str(item.get('amount', 0))) for item in split_data)
            if total_split_amount != amount:
                raise serializers.ValidationError(
                    f"Total split amount ({total_split_amount}) must equal total expense amount ({amount})."
                )

        elif split_type == 'PERCENT':
            total_percentage = sum(Decimal(str(item.get('percentage', 0))) for item in split_data)
            if total_percentage != Decimal('100.00'):
                raise serializers.ValidationError(
                    f"Total percentage must equal 100%. Current total: {total_percentage}%"
                )

        return data