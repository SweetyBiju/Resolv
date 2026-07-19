# Resolv — Debt Simplification Algorithm

This document provides a simple yet technical explanation of how **Resolv** simplifies debts among group members, reducing the total number of transactions required to settle up.

---

## 💡 The Core Problem
Imagine a group of three roommates:
1. **Alice** paid ₹1,500 for dinner.
2. **Bob** paid ₹1,500 for groceries.
3. **Charlie** owes money to both.

Without optimization:
* Bob might owe Alice ₹500.
* Charlie might owe Alice ₹500 and Bob ₹500.
This requires **three separate transactions** to settle. 

If we optimize, we look at the net balances:
* Alice paid ₹1,500 but her share was ₹1,000 → She **gets back ₹500**.
* Bob paid ₹1,500 but his share was ₹1,000 → He **gets back ₹500**.
* Charlie paid ₹0 but his share was ₹1,000 → He **owes ₹1,000**.

Instead of multiple payments, the algorithm simplifies this so **Charlie makes just two transfers** (₹500 to Alice, and ₹500 to Bob), eliminating unnecessary circular transfers.

---

## ⚙️ How the Algorithm Works (Step-by-Step)

The algorithm is housed in [expenses/utils.py](file:///c:/Users/hp/OneDrive/Desktop/Resolv/backend/expenses/utils.py) and executes in three primary stages:

### Step 1: Calculate Net Balances
For every member in the group, we calculate their total net balance.
$$\text{Net Balance} = \text{Total Paid} - \text{Total Share Owed}$$

* If $\text{Net Balance} > 0$, the member is a **Creditor** (they should receive money).
* If $\text{Net Balance} < 0$, the member is a **Debtor** (they must pay money).
* If $\text{Net Balance} = 0$, the member is completely settled.

### Step 2: Separate Debtors and Creditors
We group users into two lists based on their net balance:
1. **Debtors List:** Contains tuples of `(user_id, absolute_amount_owed)`.
2. **Creditors List:** Contains tuples of `(user_id, amount_owed_to_them)`.

### Step 3: Greedy Pairwise Matching
We sort both lists (or use a heap) so that the largest debtor is paired with the largest creditor:
1. Find the **largest debtor** (who owes the most) and the **largest creditor** (who is owed the most).
2. Compute the transaction amount:
   $$\text{Transaction Amount} = \min(\text{Amount Owed}, \text{Amount Owed to Creditor})$$
3. Record a suggested settlement payment:
   * **From:** Debtor
   * **To:** Creditor
   * **Amount:** Transaction Amount
4. Subtract the transaction amount from both the debtor's and creditor's remaining balances.
5. If the debtor still owes money, put them back on the debtor list. If the creditor is still owed money, put them back on the creditor list.
6. Repeat until all balances are fully settled (balances drop to zero).

---

## 📊 Concrete Numerical Example

Suppose we have 4 users with the following net balances:
* **User A:** $+₹600$ (Creditor)
* **User B:** $+₹400$ (Creditor)
* **User C:** $-₹700$ (Debtor)
* **User D:** $-₹300$ (Debtor)

### Algorithmic Execution Steps:

| Step | Debtors Heap / List | Creditors Heap / List | Match Action | Remaining Balances |
|---|---|---|---|---|
| **Start** | `C: -700`, `D: -300` | `A: +600`, `B: +400` | — | — |
| **Iter 1** | Largest Debtor: `C` (700)<br>Largest Creditor: `A` (600) | | **C pays A ₹600** | C still owes: `100`<br>A is settled: `0` |
| **Iter 2** | Largest Debtor: `C` (100)<br>Largest Creditor: `B` (400) | | **C pays B ₹100** | C is settled: `0`<br>B still owed: `300` |
| **Iter 3** | Largest Debtor: `D` (300)<br>Largest Creditor: `B` (300) | | **D pays B ₹300** | D is settled: `0`<br>B is settled: `0` |

### Final Suggested Settlements:
1. **User C** pays **User A** ₹600.00
2. **User C** pays **User B** ₹100.00
3. **User D** pays **User B** ₹300.00

Total Transactions: **3** (instead of potential complex individual splits).
Complexity is reduced from $O(N^2)$ direct splits to at most $O(N)$ simplified transactions.
