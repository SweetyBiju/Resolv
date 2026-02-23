import heapq
from decimal import Decimal

def simplify_debts(balances_list):
    """
    Dual-Phase Debt Simplification Algorithm.
    1. Exact-Match Pruning: Removes users with perfectly matching opposite balances.
    2. Greedy Heap-Based Netting: Minimizes transactions for the remaining group.
    
    Input format: [{'username': 'Sav', 'net_balance': -266.67}, ...]
   
    """
    
    # 1. Separate into dictionaries for easier pruning
    debtors = {item['username']: Decimal(str(item['net_balance'])) 
               for item in balances_list if item['net_balance'] < -0.01}
    
    creditors = {item['username']: Decimal(str(item['net_balance'])) 
                 for item in balances_list if item['net_balance'] > 0.01}
    
    suggested_settlements = []

    # --- PHASE 1: EXACT-MATCH PRUNING  ---
    # Goal: Find pairs like (-50, +50) and settle them immediately to reduce total participants.
    #
    debtor_names = list(debtors.keys())
    for d_name in debtor_names:
        if d_name not in debtors: continue  # Skip if already settled
        
        d_val_abs = abs(debtors[d_name])
        
        creditor_names = list(creditors.keys())
        for c_name in creditor_names:
            c_val = creditors[c_name]
            
            if abs(d_val_abs - c_val) < Decimal('0.01'):
                suggested_settlements.append({
                    "from": d_name,
                    "to": c_name,
                    "amount": float(round(c_val, 2))
                })
                # Remove both from active pools
                del debtors[d_name]
                del creditors[c_name]
                break

    # --- PHASE 2: GREEDY HEAP-BASED NETTING ---
    # For remaining complex debts, we use heaps to pair the largest debtor with the largest creditor.
    # This guarantees the minimum number of transactions.
    
    # Min-heap for debtors 
    debt_heap = []
    for name, val in debtors.items():
        heapq.heappush(debt_heap, (val, name))
        
    # Max-heap for creditors 
    cred_heap = []
    for name, val in creditors.items():
        heapq.heappush(cred_heap, (-val, name))

    while debt_heap and cred_heap:
        d_val, d_name = heapq.heappop(debt_heap)
        neg_c_val, c_name = heapq.heappop(cred_heap)
        c_val = -neg_c_val

        # Settle the minimum of the two
        settle_amount = min(abs(d_val), c_val)
        
        suggested_settlements.append({
            "from": d_name,
            "to": c_name,
            "amount": float(round(settle_amount, 2))
        })

        # Update and push back if any balance remains
        remaining_debt = d_val + settle_amount
        remaining_cred = c_val - settle_amount

        if remaining_debt < Decimal('-0.01'):
            heapq.heappush(debt_heap, (remaining_debt, d_name))
        if remaining_cred > Decimal('0.01'):
            heapq.heappush(cred_heap, (-remaining_cred, c_name))

    return suggested_settlements