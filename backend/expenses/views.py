from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from django.db.models import Sum
from django.utils import timezone
import datetime
from decimal import Decimal
from django.db.models import Q

from .models import Expense, ExpenseSplit,Settlement,ExpenseItem
from .serializers import ExpenseSerializer,SettlementSerializer
from .utils import simplify_debts
from .permissions import IsPayerOrGroupAdmin

from users.models import ReliabilityHistory

# backend/expenses/views.py

class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsPayerOrGroupAdmin] 

    def get_queryset(self):
        user = self.request.user
        # Return expenses if you are in the group, OR you paid, OR you were split on it.
        # Notice we do NOT filter by group__is_active so history is preserved.
        return Expense.objects.filter(
            Q(group__members=user) | 
            Q(paid_by=user) | 
            Q(splits__user=user),
            is_active=True
        ).distinct()
   
    def perform_create(self, serializer):
        """Automates the attribution of the payer and triggers split logic."""# Safely extract the raw ID sent from the frontend JSON payload
        paid_by_id = self.request.data.get('paid_by')
        
        if paid_by_id:
            # By using 'paid_by_id=' we can safely assign the integer directly to the DB
            expense = serializer.save(paid_by_id=paid_by_id)
        else:
            # Fallback to the logged-in user if nothing was selected
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
        elif expense.split_type == 'ITEM':
            #implementation for Item-based splitting
            for data in split_data:
                # Expects data format: {"name": "Burger", "amount": 150.00, "user_ids": [1, 2]}
                item = ExpenseItem.objects.create(expense=expense, name=data['name'], amount=Decimal(str(data['amount'])))
                item_share = item.amount / len(data['user_ids'])
                for uid in data['user_ids']:
                    ExpenseSplit.objects.create(expense=expense, item=item, user_id=uid, amount_owed=item_share)

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
            # 1. Total Paid (Active expenses only)
            total_paid = Expense.objects.filter(group=group, paid_by=member, is_active=True).aggregate(Sum('amount'))['amount__sum'] or 0
            
            # 2. Total Owed (Active expenses only)
            total_owed = ExpenseSplit.objects.filter(expense__group=group, user=member, expense__is_active=True).aggregate(Sum('amount_owed'))['amount_owed__sum'] or 0
            
            # 3. Confirmed Settlements
            settlements_sent = Settlement.objects.filter(group=group, payer=member, status__in=['CONFIRMED', 'confirmed'], is_active=True).aggregate(Sum('amount'))['amount__sum'] or 0
            settlements_received = Settlement.objects.filter(group=group, receiver=member, status__in=['CONFIRMED', 'confirmed'], is_active=True).aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Net Balance = (Paid - Owed) + (Sent - Received)
            net_balance = float(total_paid - total_owed + settlements_sent - settlements_received)
            
            results.append({
                "user_id": member.id,
                "username": member.username,
                "net_balance": round(net_balance, 2)
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

    @action(detail=True, methods=['get'], url_path='can-delete')
    def can_delete_check(self, request, pk=None):
        """
        Pre-check endpoint for the frontend to determine if an expense 
        is locked by existing settlements.
        """
        expense = self.get_object()
        group = expense.group
        splits = expense.splits.all()
        
        blocking_settlements = []
        
        for split in splits:
            debtor = split.user
            creditor = expense.paid_by
            
            if debtor == creditor:
                continue
                
            # Check for confirmed settlements between these two users in this group
            # that happened AFTER this expense was created.
            has_settled = Settlement.objects.filter(
                group=group,
                payer=debtor,
                receiver=creditor,
                status__in=['CONFIRMED', 'confirmed'],
                is_active=True,
                created_at__gte=expense.created_at
            ).exists()
            
            if has_settled:
                # Add to our list to send back to the UI
                blocking_settlements.append({
                    "debtor": debtor.username,
                    "creditor": creditor.username
                })
                
        if blocking_settlements:
            return Response({
                "can_delete": False,
                "reason": "SETTLED_DEBTS_EXIST",
                "details": blocking_settlements
            }, status=status.HTTP_200_OK)
            
        return Response({"can_delete": True}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Override the default destroy method to enforce the lock 
        on the server side during the actual DELETE call.
        """
        expense = self.get_object()
        group = expense.group
        
        # Enforce the same check directly before deletion
        for split in expense.splits.all():
            debtor = split.user
            creditor = expense.paid_by
            
            if debtor != creditor:
                has_settled = Settlement.objects.filter(
                    group=group,
                    payer=debtor,
                    receiver=creditor,
                    status__in=['CONFIRMED', 'confirmed'],
                    is_active=True,
                    created_at__gte=expense.created_at
                ).exists()
                
                if has_settled:
                    return Response(
                        {"detail": "SETTLED_DEBTS_EXIST"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # If we pass the check, perform the soft delete
        expense.is_active = False
        expense.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SettlementViewSet(viewsets.ModelViewSet):
    serializer_class = SettlementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Return settlements if you are in the group, OR you sent it, OR you received it.
        return Settlement.objects.filter(
            Q(group__members=user) | 
            Q(payer=user) | 
            Q(receiver=user),
            is_active=True
        ).distinct()
    
    def perform_create(self, serializer):
        """
        Payer initiates a settlement. Status defaults to 'PENDING'.
        """

        # SECURITY: 60s duplicate transaction check
        time_threshold = timezone.now() - datetime.timedelta(seconds=60)
        duplicate_exists = Settlement.objects.filter(
            payer=self.request.user,
            receiver=serializer.validated_data['receiver'],
            amount=serializer.validated_data['amount'],
            created_at__gte=time_threshold,
            is_active=True
        ).exists()

        if duplicate_exists:
            raise ValidationError("Duplicate settlement detected. Please wait 60 seconds.")
        serializer.save(payer=self.request.user)

    @action(detail=True, methods=['post'], url_path='confirm_settlement')
    def confirm_settlement(self, request, pk=None):
        """
        Receiver confirms they got the money. This triggers the score boost.
       
        """
        settlement = self.get_object()

        # SECURITY: Only the person receiving the money can confirm it
        if settlement.receiver != request.user:
            return Response(
                {"error": "Only the receiver can confirm this payment."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        if settlement.status == 'CONFIRMED':
            return Response({"message": "Already confirmed."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Update Settlement Status
        settlement.status = 'CONFIRMED'
        settlement.save()

        # 2. Boost Payer's Reliability Score
        # Mathematical logic: S_new = min(100.0, S_old + 0.5)
        payer = settlement.payer
        current_score = float(payer.reliability_score)
        new_score = min(100.0, current_score + 0.5)
        payer.reliability_score = new_score
        payer.save()

        # 3. Record History for the Profile Line Graph
        ReliabilityHistory.objects.create(
            user=payer,
            score=new_score,
            reason=f"Successfully settled debt with {request.user.username}"
        )

        return Response({
            "status": "confirmed",
            "new_reliability_score": new_score,
            "message": "Confetti time!" # Frontend will look for this
        }, status=status.HTTP_200_OK)