# Resolv — Complete User Flow

This document details the step-by-step user interactions and user experience journeys across **Resolv**.

---

## 🗺️ Visual User Journey Map

```
             ┌──────────────┐
             │ Registration │
             └──────┬───────┘
                    ▼
             ┌──────────────┐
             │    Login     │
             └──────┬───────┘
                    ▼
            ┌───────────────┐
            │   Dashboard   │
            └──────┬────────┘
                   │
     ┌─────────────┼──────────────┐
     ▼             ▼              ▼
┌─────────┐   ┌─────────┐   ┌───────────┐
│ Groups  │   │ Profile │   │ Analytics │
└────┬────┘   └─────────┘   └───────────┘
     │
     ├─────────────────────────────────┐
     ▼                                 ▼
┌─────────┐                       ┌───────────┐
│ Expense │                       │  Balance  │
│ Manager │                       │  Manager  │
└─────────┘                       └─────┬─────┘
                                        │
                                        ▼
                                  ┌───────────┐
                                  │Pairwise   │
                                  │Settlements│
                                  └───────────┘
```

---

## 🚪 1. Authentication & Onboarding

1. **User Sign Up:**
   * User navigates to `register.html`.
   * Enters unique username, email address, and strong password.
   * On success, user is automatically redirected to `login.html` with a success notice.
2. **User Sign In:**
   * User enters credentials on `login.html`.
   * On authorization, auth tokens are generated and stored inside the browser's `localStorage`.
   * User is redirected to `dashboard.html`.

---

## 🏡 2. The Dashboard Experience

The dashboard acts as the command center for the user:
* **Top Bar:** Displays a personalized greeting and user avatar. Clicking it reveals the user profile.
* **Groups Panel:** Lists all groups the user belongs to, including the group name, visual emoji, and current user balance status (positive or negative overall).
* **Recent Activity Feed:** Displays chronological notifications detailing actions (e.g., *"Alice added dinner expense (₹1,500.00)"*, *"Bob confirmed payment"*). Clicking an item takes the user to that group.

---

## 👥 3. Group Creation & Management

### 3.1 Creating a Group
1. From the dashboard or groups view, the user clicks **Create Group**.
2. Fills in the name, chooses the group's base currency (e.g., `INR`, `USD`), selects an identifying emoji, and enters an optional description.
3. Clicking **Create** redirects the user directly into the newly created **Group Details** view as the group's `ADMIN`.

### 3.2 Inviting Members
* The admin clicks the **Invite Code** button to open the modal.
* The modal generates an 8-character unique alphanumeric key (e.g., `X9F2A1C4`).
* The admin shares this key with friends.
* Friends click **Join Group** on their dashboard, input the code, and are instantly added to the group roster.

---

## 💸 4. Collaborative Spending (Expense Lifecycles)

### 4.1 Creating Expenses
1. In the **Group Details** page, members click **Add Expense**.
2. Enters description title, bill amount, category, date, and chooses who paid the bill.
3. Selects a **Split Method**:
   * **Equal:** Evenly divides the bill among all group members.
   * **Exact:** User types the exact currency share amount owed by each member (validated to sum to the bill total).
   * **Percent:** User enters percentage shares (validated to sum to 100%).
   * **By Item:** User adds list items with prices and checks checkboxes indicating which members shared each item.
4. Clicking **Save** registers the splits and creates a notification inside the activity feed.

---

## 🤝 5. Balances & Debt Settlement Lifecycle

### 5.1 Understanding Net Balances
Inside the group view, the **Balances** tab provides clear status indicators:
* **gets back ₹X:** Displayed in blue if the group member paid more than their share and is owed money overall.
* **owes ₹X:** Displayed in red if the group member owes money overall.
* **Personal Balance Hero Banner:** Displays a prominent hero message summarizing: *"You owe ₹X overall"* or *"You are owed ₹X overall"*.

### 5.2 Pairwise suggested payments (Settlement Flow)
1. Resolv simplifies circular debt to generate direct suggested payouts:
   * Example: *"You owe Bob ₹500.00"* or *"Charlie owes you ₹300.00"*.
2. To pay off debt, a user clicks **Record Settlement** or clicks the action button next to a suggestion.
3. Input amount, currency, and submit. The settlement starts in a **PENDING** state.
4. **Receiver Confirmation:**
   * The payee receives a notification indicating a pending payment from the payer.
   * The payee must click **Confirm** (verifying they received the cash/transfer) to mark the settlement as **CONFIRMED**.
   * If the payment details were incorrect, the payee or payer can click **Cancel** to invalidate it.
5. On confirmation, the payer's **Reliability Score** increments by `+0.5` points (capped at `100.00`).

---

## 📊 6. Budgeting & Financial Auditing

1. User goes to the **Analytics** page.
2. Selects a group filter or views cumulative metrics.
3. **Trends Chart:** Renders interactive month-over-month spending charts.
4. **Category Breakdown:** Displays a donut chart highlighting budget share distributions (Food, Travel, Housing, etc.).
5. **Budgets Manager:**
   * Displays progress bars comparing spending against monthly category budgets.
   * If actual spending exceeds the limit, the progress bar turns red.
   * Users click the **Edit (pencil)** icon to set/adjust budgets for the current month.
6. **Export Data:** Users click **Export CSV** to download a complete spreadsheet of transactions for auditing.
