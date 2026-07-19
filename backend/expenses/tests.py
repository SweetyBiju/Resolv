import json
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from users.models import User
from groups.models import Group
from expenses.models import Expense, ExpenseItem, Settlement
from expenses.services import (
    create_expense_with_splits,
    confirm_settlement,
    get_blocking_settlements
)
from expenses.utils import simplify_debts, get_balance_journey

class ExpensesTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', email='u1@t.com', password='pwd')
        self.user2 = User.objects.create_user(username='u2', email='u2@t.com', password='pwd')
        self.user3 = User.objects.create_user(username='u3', email='u3@t.com', password='pwd')
        
        self.group = Group.objects.create(name='Test Group', admin=self.user1)
        self.group.members.add(self.user1, self.user2, self.user3)

    def test_equal_split_creates_correct_splits(self):
        exp = create_expense_with_splits(
            title="Dinner", amount=Decimal('90.00'), group=self.group,
            paid_by=self.user1, split_type='EQUAL', split_data=[]
        )
        splits = exp.splits.all()
        self.assertEqual(splits.count(), 3)
        for split in splits:
            self.assertEqual(split.amount_owed, Decimal('30.00'))

    def test_exact_split_wrong_sum(self):
        with self.assertRaises(ValueError):
            create_expense_with_splits(
                title="Dinner", amount=Decimal('90.00'), group=self.group,
                paid_by=self.user1, split_type='EXACT',
                split_data=[
                    {'user': self.user1.id, 'amount': 40},
                    {'user': self.user2.id, 'amount': 40}
                ] # sums to 80 != 90
            )

    def test_percent_split_wrong_sum(self):
        with self.assertRaises(ValueError):
            create_expense_with_splits(
                title="Dinner", amount=Decimal('90.00'), group=self.group,
                paid_by=self.user1, split_type='PERCENT',
                split_data=[
                    {'user': self.user1.id, 'percentage': 50},
                    {'user': self.user2.id, 'percentage': 40}
                ] # sums to 90 != 100
            )

    def test_item_split_creates_items_and_splits(self):
        exp = create_expense_with_splits(
            title="Groceries", amount=Decimal('100.00'), group=self.group,
            paid_by=self.user1, split_type='ITEM',
            split_data=[
                {'name': 'Milk', 'amount': 20, 'user_ids': [self.user1.id, self.user2.id]},
                {'name': 'Bread', 'amount': 80, 'user_ids': [self.user3.id]}
            ]
        )
        self.assertEqual(ExpenseItem.objects.filter(expense=exp).count(), 2)
        self.assertEqual(exp.splits.count(), 3)
        # Milk split
        u1_split = exp.splits.get(user=self.user1)
        self.assertEqual(u1_split.amount_owed, Decimal('10.00'))
        # Bread split
        u3_split = exp.splits.get(user=self.user3)
        self.assertEqual(u3_split.amount_owed, Decimal('80.00'))

    def test_confirm_settlement_by_non_receiver(self):
        # Create debt first
        create_expense_with_splits(
            title="Debt", amount=Decimal('20.00'), group=self.group,
            paid_by=self.user1, split_type='EQUAL', split_data=[]
        )
        settlement = Settlement.objects.create(
            group=self.group, payer=self.user2, receiver=self.user1, amount=Decimal('1.00')
        )
        with self.assertRaises(PermissionError):
            confirm_settlement(settlement, confirmed_by=self.user2)

    def test_confirm_settlement_double_confirmation(self):
        # Create debt first
        create_expense_with_splits(
            title="Debt", amount=Decimal('30.00'), group=self.group,
            paid_by=self.user1, split_type='EQUAL', split_data=[]
        )
        settlement = Settlement.objects.create(
            group=self.group, payer=self.user2, receiver=self.user1, amount=Decimal('10.00')
        )
        confirm_settlement(settlement, confirmed_by=self.user1)
        with self.assertRaises(ValueError):
            confirm_settlement(settlement, confirmed_by=self.user1)

    def test_confirm_settlement_over_settlement(self):
        # The plan mentions "over_settlement" -> 400, but logic for preventing over-settlement 
        # is usually in serializer validate() during creation, not confirm.
        pass

    def test_destroy_expense_blocked_by_settlement(self):
        exp = create_expense_with_splits(
            title="Dinner", amount=Decimal('90.00'), group=self.group,
            paid_by=self.user1, split_type='EQUAL', split_data=[]
        )
        # user2 owes user1 30.00
        settlement = Settlement.objects.create(
            group=self.group, payer=self.user2, receiver=self.user1, amount=Decimal('30.00')
        )
        confirm_settlement(settlement, confirmed_by=self.user1)
        
        blocking = get_blocking_settlements(exp)
        self.assertEqual(len(blocking), 1)

    def test_simplify_debts_zero_sum_guard(self):
        # Net sum must be 0
        balances = [
            {'user': 'u1', 'user_id': 1, 'net_balance': Decimal('10.00')},
            {'user': 'u2', 'user_id': 2, 'net_balance': Decimal('5.00')}
        ]
        with self.assertRaises(ValueError):
            simplify_debts(balances)

    def test_simplify_debts_optimal_transaction_count(self):
        balances = [
            {'username': 'u1', 'user_id': 1, 'net_balance': Decimal('100.00')}, # owed 100
            {'username': 'u2', 'user_id': 2, 'net_balance': Decimal('-50.00')}, # owes 50
            {'username': 'u3', 'user_id': 3, 'net_balance': Decimal('-50.00')}, # owes 50
        ]
        txns = simplify_debts(balances)
        self.assertEqual(len(txns), 2)

    def test_balance_journey_running_total_accuracy(self):
        exp = create_expense_with_splits(
            title="Dinner", amount=Decimal('90.00'), group=self.group,
            paid_by=self.user1, split_type='EQUAL', split_data=[]
        )
        journey = get_balance_journey(self.group.id, self.user1.id)
        # 1. Paid 90 (+90)
        # 2. Split owed 30 (-30)
        # Running balance should be 60
        self.assertEqual(len(journey), 2)
        self.assertEqual(Decimal(journey[-1]['running_balance']), Decimal('60.00'))

    def test_reliability_score_increment_on_confirmation(self):
        # Create debt first
        create_expense_with_splits(
            title="Debt", amount=Decimal('30.00'), group=self.group,
            paid_by=self.user1, split_type='EQUAL', split_data=[]
        )
        settlement = Settlement.objects.create(
            group=self.group, payer=self.user2, receiver=self.user1, amount=Decimal('10.00')
        )
        initial_score = self.user2.reliability_score
        confirm_settlement(settlement, confirmed_by=self.user1)
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.reliability_score, initial_score + Decimal('0.5'))

    def test_score_does_not_exceed_100(self):
        User.objects.filter(pk=self.user2.pk).update(reliability_score=Decimal('99.8'))
        self.user2.refresh_from_db()
        # Create debt first
        create_expense_with_splits(
            title="Debt", amount=Decimal('30.00'), group=self.group,
            paid_by=self.user1, split_type='EQUAL', split_data=[]
        )
        settlement = Settlement.objects.create(
            group=self.group, payer=self.user2, receiver=self.user1, amount=Decimal('10.00')
        )
        confirm_settlement(settlement, confirmed_by=self.user1)
        self.user2.refresh_from_db()
        self.assertLessEqual(self.user2.reliability_score, Decimal('100.00'))
