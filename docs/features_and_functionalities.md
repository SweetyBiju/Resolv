# Resolv — Features & Functionalities

This document lists all features and functionalities currently supported by the **Resolv** application.

---

## 🔒 1. User Account & Authentication
* **User Registration & Log In:** Secure token-based access utilizing JSON Web Tokens (JWT) on the backend.
* **Device Logout:** Users can log out of their current session, or trigger a "Logout All Devices" request to invalidate all refresh tokens.
* **Reliability Metrics:** Tracks user payment reliability scores (starting at `70.00` and fluctuating based on settlement confirmations).

---

## 👥 2. Group Expense Management
* **Group Creation:** Customization options including group name, description, active currency (`INR`, `USD`, `EUR`, `GBP`, `SGD`), and a distinct visual emoji.
* **Invite Roster System:** Automatically generates 8-character unique invite codes. Friends use the code to instantly join the group.
* **Admin Privilege Controls:** The creator is automatically assigned as `ADMIN`. Admins can invite/remove members or transfer admin ownership.
* **Orphan Protection Guard:** Admins cannot leave or delete themselves from a group without transferring admin rights first.

---

## 💸 3. Expense Sharing Engine
* **Multiple Split Algorithms:**
  * **EQUAL:** Automatically divides the total expense evenly among all members.
  * **EXACT:** Allows specifying exact monetary amounts for each member.
  * **PERCENT:** Splits the bill by percentage values.
  * **ITEMIZED (By Item):** Allocates cost per item line, splitting each item's cost only among selected users.
* **Floating-point rounding guard:** Automatically corrects decimal rounding remainders (e.g. dividing ₹100.00 among 3 people resolves as ₹33.34 for the first person, and ₹33.33 for the remaining two), maintaining exact penny-perfect balances.
* **Image Receipt Upload:** Integrates optional receipt URLs or image paths into expense records.

---

## 🤝 4. Suggested Settlements & Debt Optimization
* **Pairwise Debt Simplification:** Simplifies complex multi-user debts to the absolute minimum number of payments (e.g., matching the highest debtors with the highest creditors).
* **Clear Balances View:** Provides a personal hero banner ("You owe ₹X overall" or "You gets back ₹X overall") alongside explicit "gets back ₹X" (blue) and "owes ₹X" (red) status labels for every member.

---

## 🛡️ 5. Settlement Safeguard Workflows
* **Pending Verification Loop:** When a member makes a payment, the settlement is registered as `PENDING`. It is only confirmed once the receiving user verifies they received the money, preventing fake settlement fraud.
* **Payer Reliability score:** Successful settlements increase the payer's score by `+0.5` points (capped at `100.00`).
* **Deletion Safeguards:**
  * Expenses involved in settled transactions cannot be deleted.
  * Groups cannot be deleted if there are pending, unresolved balances between members.

---

## 📊 6. Analytics & Budgeting Tools
* **Interactive Charting:** Displays spending trends over time and category breakdown charts.
* **Pencil Budget Adjustments:** Set category-level monthly budgets. Visual progress bars indicate spending percentage and turn red if you exceed your limit.
* **CSV Export:** Users can download a spreadsheet containing all transaction splits and logs.

---

## 📋 7. Activity Audit Logs
* **Real-time logs:** Logs every structural action (creating group, adding member, editing expense, confirming settlement).
* **Frontend parser:** Parses backend action logs into clear natural sentences on the dashboard and activity pages.
