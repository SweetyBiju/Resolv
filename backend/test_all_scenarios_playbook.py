import os
import sys
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.development')
django.setup()

from django.test import Client
from users.models import User
from groups.models import Group, GroupMembership
from expenses.models import Expense, Settlement
from groups import services as group_services
from expenses import services as expense_services
from expenses import utils as expense_utils
from analytics import services as analytics_services

def run_playbook_verification():
    print("=" * 60)
    print("      RESOLV USER SCENARIOS PLAYBOOK VERIFICATION")
    print("=" * 60)
    
    results = []
    client = Client(HTTP_HOST='localhost')

    def record_result(section, scenario, passed, detail=""):
        status = "PASSED" if passed else "FAILED"
        results.append((section, scenario, status, detail))
        print(f"[{status}] {section} - {scenario}: {detail}")

    # -------------------------------------------------------------
    # SECTION 1: Auth & Account Management
    # -------------------------------------------------------------
    section = "Section 1: Auth & Account"
    
    # 1.1 Signup
    email = "playbook_user1@test.com"
    passw = "Pass1234!@#"
    User.objects.filter(email=email).delete()
    
    resp = client.post('/api/v1/users/register/', {
        "username": "playbook1",
        "email": email,
        "password": passw
    }, content_type='application/json')
    
    created_user = User.objects.filter(email=email).first()
    if resp.status_code == 201 and created_user and created_user.reliability_score == Decimal('70.00'):
        record_result(section, "1.1 Signup (Happy Path)", True, "Created with default score 70.00")
    else:
        record_result(section, "1.1 Signup (Happy Path)", False, f"Status: {resp.status_code}, Score: {created_user.reliability_score if created_user else None}")

    # 1.2 Signup Validation Errors (Duplicate Email)
    resp = client.post('/api/v1/users/register/', {
        "username": "playbook1_dup",
        "email": email,
        "password": passw
    }, content_type='application/json')
    if resp.status_code == 400:
        record_result(section, "1.2 Signup (Validation Errors)", True, "Caught duplicate email 400")
    else:
        record_result(section, "1.2 Signup (Validation Errors)", False, f"Expected 400, got {resp.status_code}")

    # 1.3 Login (Happy Path)
    resp = client.post('/api/v1/auth/login/', {
        "email": email,
        "password": passw
    }, content_type='application/json')
    if resp.status_code == 200 and 'access' in resp.json():
        tokens = resp.json()
        token = tokens['access']
        record_result(section, "1.3 Login (Happy Path)", True, "Received JWT access token")
    else:
        record_result(section, "1.3 Login (Happy Path)", False, f"Status {resp.status_code}")
        token = None

    # 1.4 Login Wrong Password
    resp = client.post('/api/v1/auth/login/', {
        "email": email,
        "password": "WrongPassword123"
    }, content_type='application/json')
    if resp.status_code == 401:
        record_result(section, "1.4 Login (Wrong Password)", True, "Returned 401 Unauthorized")
    else:
        record_result(section, "1.4 Login (Wrong Password)", False, f"Expected 401, got {resp.status_code}")

    # 1.5 Change Password
    if token:
        resp = client.post('/api/v1/users/change-password/', {
            "old_password": passw,
            "new_password": "NewPass1234!@#"
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        if resp.status_code == 200:
            record_result(section, "1.5 Change Password", True, "Password updated successfully")
            passw = "NewPass1234!@#"
        else:
            record_result(section, "1.5 Change Password", False, f"Status {resp.status_code}, Body: {resp.content.decode('utf-8', errors='ignore')}")

    # -------------------------------------------------------------
    # SECTION 2: Groups & Memberships
    # -------------------------------------------------------------
    section = "Section 2: Groups"

    # Setup test users
    u1, _ = User.objects.get_or_create(username='g_alice', defaults={'email':'galice@test.com'})
    u2, _ = User.objects.get_or_create(username='g_bob', defaults={'email':'gbob@test.com'})
    u3, _ = User.objects.get_or_create(username='g_charlie', defaults={'email':'gcharlie@test.com'})

    # 2.1 Create Group
    grp = group_services.create_group(name="Goa Trip Playbook", admin_user=u1, currency="INR", emoji="🏖️")
    if grp and grp.admin == u1 and GroupMembership.objects.filter(group=grp, user=u1, role='ADMIN').exists():
        record_result(section, "2.1 Create Group", True, f"Group ID {grp.id} created with Admin u1")
    else:
        record_result(section, "2.1 Create Group", False, "Failed to create group with admin membership")

    # 2.2 Join via Invite Code
    inv_code = grp.invite_code
    joined_grp = group_services.join_via_invite(inv_code, u2)
    if joined_grp.id == grp.id and grp.members.filter(id=u2.id).exists():
        record_result(section, "2.2 Join via Invite Code", True, "u2 joined via invite code")
    else:
        record_result(section, "2.2 Join via Invite Code", False, "Join failed")

    # 2.3 Invite Code Rotation
    old_code = grp.invite_code
    new_code = group_services.regenerate_invite_code(grp, u1)
    grp.refresh_from_db()
    if old_code != new_code and grp.invite_code == new_code:
        record_result(section, "2.3 Regenerate Invite Code", True, f"Rotated {old_code} -> {new_code}")
    else:
        record_result(section, "2.3 Regenerate Invite Code", False, "Regeneration failed")

    # 2.4 Add Member Manually
    group_services.add_member(grp, u3, added_by=u1)
    if grp.members.filter(id=u3.id).exists():
        record_result(section, "2.4 Add Member Manually", True, "u3 added manually")
    else:
        record_result(section, "2.4 Add Member Manually", False, "Add member failed")

    # 2.6 Remove Member Balance Guard (when 0 balance)
    group_services.remove_member(grp, u3, removed_by=u1)
    if not grp.members.filter(id=u3.id).exists():
        record_result(section, "2.6 Remove Member (Zero Balance)", True, "u3 removed successfully")
    else:
        record_result(section, "2.6 Remove Member (Zero Balance)", False, "u3 still in group")

    # Re-add u3
    group_services.add_member(grp, u3, added_by=u1)

    # 2.7 Transfer Admin & 2.8 Orphan Guard
    try:
        group_services.remove_member(grp, u1, removed_by=u1)
        record_result(section, "2.8 Orphan Guard", False, "Allowed removing active admin without transfer!")
    except ValueError as e:
        record_result(section, "2.8 Orphan Guard", True, f"Blocked removing admin: '{e}'")

    group_services.transfer_admin(grp, new_admin=u2, requested_by=u1)
    grp.refresh_from_db()
    if grp.admin == u2:
        record_result(section, "2.7 Transfer Admin Rights", True, "Admin transferred to u2")
        # Transfer back to u1 for remaining tests
        group_services.transfer_admin(grp, new_admin=u1, requested_by=u2)
    else:
        record_result(section, "2.7 Transfer Admin Rights", False, "Transfer failed")

    # -------------------------------------------------------------
    # SECTION 3: Expenses
    # -------------------------------------------------------------
    section = "Section 3: Expenses"

    # 3.1 Equal Split
    exp_eq = expense_services.create_expense_with_splits(
        title="Dinner Equal", amount=Decimal('600.00'), group=grp, paid_by=u1, split_type='EQUAL', split_data=[]
    )
    splits = exp_eq.splits.all()
    if len(splits) == 3 and sum(s.amount_owed for s in splits) == Decimal('600.00'):
        record_result(section, "3.1 Equal Split", True, "3 splits created summing to 600.00")
    else:
        record_result(section, "3.1 Equal Split", False, f"Splits: {[s.amount_owed for s in splits]}")

    # 3.2 Exact Split Valid & 3.3 Exact Split Validation Failure
    try:
        expense_services.create_expense_with_splits(
            title="Exact Invalid", amount=Decimal('5000.00'), group=grp, paid_by=u1, split_type='EXACT',
            split_data=[{'user': u1.id, 'amount': 2500}, {'user': u2.id, 'amount': 2600}]
        )
        record_result(section, "3.3 Exact Split Validation Failure", False, "Allowed mismatched sum 5100 vs 5000!")
    except ValueError as e:
        record_result(section, "3.3 Exact Split Validation Failure", True, f"Caught sum mismatch: '{e}'")

    exp_exact = expense_services.create_expense_with_splits(
        title="Exact Valid", amount=Decimal('5000.00'), group=grp, paid_by=u1, split_type='EXACT',
        split_data=[{'user': u1.id, 'amount': 2500}, {'user': u2.id, 'amount': 2500}]
    )
    if exp_exact.splits.count() == 2:
        record_result(section, "3.2 Exact Split Valid", True, "2 exact splits created successfully")
    else:
        record_result(section, "3.2 Exact Split Valid", False, "Failed exact split creation")

    # 3.4 Percent Split
    exp_pct = expense_services.create_expense_with_splits(
        title="Percent Hotel", amount=Decimal('9000.00'), group=grp, paid_by=u1, split_type='PERCENT',
        split_data=[{'user': u1.id, 'percentage': 50}, {'user': u2.id, 'percentage': 30}, {'user': u3.id, 'percentage': 20}]
    )
    pct_shares = {s.user_id: s.amount_owed for s in exp_pct.splits.all()}
    if pct_shares[u1.id] == Decimal('4500.00') and pct_shares[u2.id] == Decimal('2700.00') and pct_shares[u3.id] == Decimal('1800.00'):
        record_result(section, "3.4 Percent Split", True, "Shares: 4500, 2700, 1800")
    else:
        record_result(section, "3.4 Percent Split", False, f"Shares: {pct_shares}")

    # 3.5 Item-by-item Split
    exp_item = expense_services.create_expense_with_splits(
        title="Itemized Lunch", amount=Decimal('800.00'), group=grp, paid_by=u1, split_type='ITEM',
        split_data=[
            {'name': 'Burger', 'amount': 200, 'user_ids': [u1.id, u2.id]},
            {'name': 'Pizza', 'amount': 600, 'user_ids': [u3.id]}
        ]
    )
    if exp_item.items.count() == 2 and exp_item.splits.count() == 3:
        record_result(section, "3.5 Itemized Split", True, "Items and splits created cleanly")
    else:
        record_result(section, "3.5 Itemized Split", False, f"Items: {exp_item.items.count()}, Splits: {exp_item.splits.count()}")

    # -------------------------------------------------------------
    # SECTION 4 & 5: Debt Calculations, Settlements & Complex Scenarios
    # -------------------------------------------------------------
    section = "Section 4 & 5: Debt & Settlements"

    # Clean test group for 3-Person Circular Debt Scenario (Section 5.2)
    c_group = group_services.create_group(name="Circular Debt Group", admin_user=u1, currency="INR")
    group_services.add_member(c_group, u2, u1)
    group_services.add_member(c_group, u3, u1)

    # Hotel: u1 pays 3000 (equal)
    exp_hotel = expense_services.create_expense_with_splits("Hotel", Decimal('3000'), c_group, u1, 'EQUAL', [])
    # Petrol: u2 pays 600 (equal)
    expense_services.create_expense_with_splits("Petrol", Decimal('600'), c_group, u2, 'EQUAL', [])
    # Food: u3 pays 900 (equal)
    expense_services.create_expense_with_splits("Food", Decimal('900'), c_group, u3, 'EQUAL', [])

    # Test debt optimization
    bals = expense_utils.compute_group_balances(c_group.id)
    sug = expense_utils.simplify_debts(bals)

    if len(sug) == 2:
        record_result(section, "5.2 3-Person Circular Debt Optimization", True, f"Reduced 6 debts to 2 transactions: {sug}")
    else:
        record_result(section, "5.2 3-Person Circular Debt Optimization", False, f"Expected 2 transactions, got {len(sug)}: {sug}")

    # 4.3 Settlement Confirmation & Reliability Score
    initial_score = u2.reliability_score
    stl = Settlement.objects.create(group=c_group, payer=u2, receiver=u1, amount=Decimal('900.00'), currency='INR')
    
    # Non-receiver confirm guard
    try:
        expense_services.confirm_settlement(stl, confirmed_by=u2)
        record_result(section, "4.3 Receiver Guard", False, "Payer allowed to confirm settlement!")
    except PermissionError:
        record_result(section, "4.3 Receiver Guard", True, "Blocked non-receiver confirmation")

    # Receiver confirms
    res = expense_services.confirm_settlement(stl, confirmed_by=u1)
    stl.refresh_from_db()
    u2.refresh_from_db()
    if stl.status == 'CONFIRMED' and u2.reliability_score == initial_score + Decimal('0.50'):
        record_result(section, "4.3 Settlement Confirmation & Score Bump", True, f"Score bumped from {initial_score} to {u2.reliability_score}")
    else:
        record_result(section, "4.3 Settlement Confirmation & Score Bump", False, f"Status: {stl.status}, Score: {u2.reliability_score}")

    # 4.6 Over-settlement Guard
    stl_over = Settlement.objects.create(group=c_group, payer=u2, receiver=u1, amount=Decimal('500.00'), currency='INR')
    try:
        expense_services.confirm_settlement(stl_over, confirmed_by=u1)
        record_result(section, "4.6 Over-Settlement Guard", False, "Over-settlement allowed!")
    except ValueError as e:
        record_result(section, "4.6 Over-Settlement Guard", True, f"Caught over-settlement: '{e}'")

    # 5.4 Deletion Safeguards (Rage Quit sequence)
    # Check blocking settlements for exp_hotel (since stl is confirmed for u2 paying u1 for exp_hotel)
    blocking = expense_services.get_blocking_settlements(exp_hotel)
    if blocking:
        record_result(section, "5.4 Expense Deletion Guard (Settled)", True, f"Found blocking settlements: {blocking}")
    else:
        record_result(section, "5.4 Expense Deletion Guard (Settled)", False, "No blocking settlements found")

    try:
        group_services.delete_group(c_group, u1)
        record_result(section, "5.4 Group Deletion Guard (Unsettled)", False, "Allowed deleting group with active debts!")
    except ValueError as e:
        record_result(section, "5.4 Group Deletion Guard (Unsettled)", True, f"Blocked group delete: '{e}'")

    # -------------------------------------------------------------
    # SECTION 6: Analytics & Budgets
    # -------------------------------------------------------------
    section = "Section 6: Analytics"
    
    bva = analytics_services.get_budget_vs_actual(u1, c_group.id, 7, 2026)
    if isinstance(bva, list):
        record_result(section, "6.3 Budget vs Actual Calculations", True, f"Returned {len(bva)} category entries")
    else:
        record_result(section, "6.3 Budget vs Actual Calculations", False, f"Returned {type(bva)}")

    # -------------------------------------------------------------
    # SUMMARY REPORT
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    print("                VERIFICATION SUMMARY REPORT")
    print("=" * 60)
    passed_count = sum(1 for r in results if r[2] == "PASSED")
    failed_count = sum(1 for r in results if r[2] == "FAILED")
    print(f"Total Scenarios Tested: {len(results)}")
    print(f"Passed: {passed_count} | Failed: {failed_count}\n")
    for r in results:
        print(f"[{r[2]}] {r[0]} - {r[1]}")

if __name__ == '__main__':
    run_playbook_verification()
