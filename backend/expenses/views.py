from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from decimal import Decimal
from .models import Expense, ExpenseSplit
from .serializers import ExpenseSerializer

from rest_framework.decorators import action
from django.db.models import Sum

from .utils import simplify_debts

# backend/expenses/views.py

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def perform_create(self, serializer):
        """Automates the attribution of the payer and triggers split logic."""
        expense = serializer.save(paid_by=self.request.user)
        self.calculate_splits(expense, self.request.data.get('split_data', []))

    def calculate_splits(self, expense, split_data):
        """Handles the mathematical distribution of debt."""
        group_members = expense.group.members.all()
        member_count = group_members.count()

        # FIX: Prevent DivisionByZero if group is empty
        if member_count == 0:
            return 

       
        if expense.split_type == 'EQUAL':
            share = expense.amount / member_count
            for member in group_members:
                ExpenseSplit.objects.create(
                    expense=expense,
                    user=member,
                    amount_owed=share
                )
        elif expense.split_type == 'EXACT':
            # Directly use the amounts provided in split_data
            for data in split_data:
                ExpenseSplit.objects.create(
                    expense=expense, 
                    user_id=data['user'], 
                    amount_owed=Decimal(str(data['amount']))
                )

        elif expense.split_type == 'PERCENT':
            # Calculate amount based on the total bill percentage
            for data in split_data:
                share = (Decimal(str(data['percentage'])) / 100) * expense.amount
                ExpenseSplit.objects.create(
                    expense=expense, 
                    user_id=data['user'], 
                    amount_owed=share
                )

    @action(detail=False, methods=['get'], url_path='balances/(?P<group_id>[^/.]+)')
    def group_balances(self, request, group_id=None):
        """Aggregates net financial standing for every group member."""
        from groups.models import Group
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            return Response({"error": "Group not found"}, status=404)
            
        members = group.members.all()
        results = []

        for member in members:
            total_paid = Expense.objects.filter(group=group, paid_by=member).aggregate(Sum('amount'))['amount__sum'] or 0
            total_owed = ExpenseSplit.objects.filter(expense__group=group, user=member).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
            
            results.append({
                "user_id": member.id,
                "username": member.username,
                "net_balance": float(total_paid - total_owed)
            })
        return Response(results)

    @action(detail=False, methods=['get'], url_path='suggested-settlements/(?P<group_id>[^/.]+)')
    def suggested_settlements(self, request, group_id=None):
        """Runs the Dual-Phase Algorithm to return minimal transactions."""
        balances_response = self.group_balances(request, group_id=group_id)
        if balances_response.status_code != 200:
            return balances_response
            
        settlements = simplify_debts(balances_response.data)
        return Response({
            "group_id": group_id,
            "suggested_payments": settlements
        })