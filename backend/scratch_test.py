import os
import django
from decimal import Decimal
import threading

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.development')
django.setup()

from users.models import User
from groups.models import Group, GroupMembership
from expenses.models import Expense, Settlement
from expenses.services import create_expense_with_splits, confirm_settlement, get_blocking_settlements

def run_tests():
    # Setup test users
    alice, _ = User.objects.get_or_create(username='alice_scen', email='al@test.com')
    bob, _ = User.objects.get_or_create(username='bob_scen', email='bob@test.com')
    charlie, _ = User.objects.get_or_create(username='charlie_scen', email='ch@test.com')
    
    # Setup test group
    group, _ = Group.objects.get_or_create(name='Scenarios', currency='INR')
    GroupMembership.objects.get_or_create(group=group, user=alice, role='ADMIN')
    GroupMembership.objects.get_or_create(group=group, user=bob, role='MEMBER')
    GroupMembership.objects.get_or_create(group=group, user=charlie, role='MEMBER')

    print("\n=== 1. The over-settlement trap ===")
    exp1 = create_expense_with_splits(
        title="Trap", amount=Decimal('100'), group=group, paid_by=alice, split_type='EQUAL', split_data=[]
    )
    settle1 = Settlement.objects.create(group=group, payer=bob, receiver=alice, amount=Decimal('60'), currency='INR')
    try:
        confirm_settlement(settle1, alice)
        print("[FAIL] Over-settlement allowed!")
    except ValueError as e:
        print(f"[PASS] Caught over-settlement: {e}")

    print("\n=== 2. Delete an expense that has a pending/confirmed settlement ===")
    # Create a settlement for the remaining debt
    settle2 = Settlement.objects.create(group=group, payer=bob, receiver=alice, amount=Decimal('33.33'), currency='INR')
    confirm_settlement(settle2, alice)
    blocking = get_blocking_settlements(exp1)
    if blocking:
        print(f"[PASS] Guard triggered! Blocking settlements found: {blocking}")
    else:
        print("[FAIL] No blocking settlements found!")
        
    print("\n=== 3. The EXACT split rounding mine field ===")
    exp3 = create_expense_with_splits(
        title="Three-way", amount=Decimal('100'), group=group, paid_by=alice, split_type='EQUAL', split_data=[]
    )
    splits = exp3.splits.all()
    total_split = sum(s.amount_owed for s in splits)
    if total_split == Decimal('100.00'):
        print(f"[PASS] Splits sum exactly to 100. Values: {[s.amount_owed for s in splits]}")
    else:
        print(f"[FAIL] Splits sum to {total_split} instead of 100! Values: {[s.amount_owed for s in splits]}")

    print("\n=== 4. Non-receiver tries to confirm a settlement ===")
    settle4 = Settlement.objects.create(group=group, payer=charlie, receiver=alice, amount=Decimal('10'), currency='INR')
    try:
        confirm_settlement(settle4, charlie) # bob/charlie tries to confirm payment to alice
        print("[FAIL] Non-receiver allowed to confirm!")
    except PermissionError as e:
        print(f"[PASS] Caught auth bypass: {e}")

    print("\n=== 5. Duplicate settlement + rapid-fire confirm race condition ===")
    settle5 = Settlement.objects.create(group=group, payer=charlie, receiver=alice, amount=Decimal('10'), currency='INR')
    
    results = []
    def confirm_thread():
        # Django requires new DB connections for new threads sometimes, 
        # but for this simple test let's see if select_for_update handles it
        try:
            confirm_settlement(settle5, alice)
            results.append("SUCCESS")
        except Exception as e:
            results.append(f"ERROR: {type(e).__name__} - {e}")
            
    t1 = threading.Thread(target=confirm_thread)
    t2 = threading.Thread(target=confirm_thread)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print(f"[RACE RESULTS]: {results}")

if __name__ == '__main__':
    run_tests()
