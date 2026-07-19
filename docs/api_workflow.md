# Resolv — End-to-End API Workflow

This document details the complete end-to-end REST API workflows for **Resolv**, covering the request/response payloads and sequence of operations for authentication, group management, expense tracking, debt settlements, and analytics.

---

## 🔑 1. Authentication Workflow

### 1.1 User Registration
* **Endpoint:** `POST /api/v1/users/register/`
* **Request Body:**
  ```json
  {
    "username": "alice123",
    "email": "alice@resolv.com",
    "password": "StrongPassword!123"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "id": 5,
    "username": "alice123",
    "email": "alice@resolv.com",
    "currency_preference": "INR",
    "reliability_score": "70.00"
  }
  ```

### 1.2 User Login (Token Generation)
* **Endpoint:** `POST /api/v1/auth/login/`
* **Request Body:**
  ```json
  {
    "email": "alice@resolv.com",
    "password": "StrongPassword!123"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsIn...",
    "access": "eyJhbGciOiJIUzI1NiIsIn..."
  }
  ```
* **Note:** The `access` token must be included in the header of all authenticated requests as `Authorization: Bearer <access_token>`.

### 1.3 Token Refresh
* **Endpoint:** `POST /api/v1/auth/token/refresh/`
* **Request Body:**
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsIn..."
  }
  ```

---

## 👥 2. Group Management Workflow

### 2.1 Create Group
* **Endpoint:** `POST /api/v1/groups/`
* **Request Body:**
  ```json
  {
    "name": "Flat 302 Expenses",
    "currency": "INR",
    "emoji": "🏠",
    "description": "Shared household bills and groceries"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "id": 12,
    "name": "Flat 302 Expenses",
    "currency": "INR",
    "emoji": "🏠",
    "description": "Shared household bills and groceries",
    "invite_code": "X9F2A1C4",
    "admin": 5,
    "member_count": 1,
    "created_at": "2026-07-19T12:00:00Z"
  }
  ```

### 2.2 Join Group via Invite Code
* **Endpoint:** `POST /api/v1/groups/join/`
* **Request Body:**
  ```json
  {
    "invite_code": "X9F2A1C4"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "message": "Successfully joined group.",
    "group_id": 12
  }
  ```

### 2.3 Add Group Member Manually (Admin Only)
* **Endpoint:** `POST /api/v1/groups/12/add_member/`
* **Request Body:**
  ```json
  {
    "email_or_username": "bob456"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "status": "Member added successfully."
  }
  ```

### 2.4 Regenerate Group Invite Code (Admin Only)
* **Endpoint:** `POST /api/v1/groups/12/regenerate_invite/`
* **Request Body:** `{}`
* **Response (200 OK):**
  ```json
  {
    "invite_code": "A8C2B3E9"
  }
  ```

---

## 💸 3. Expense Tracking Workflow

### 3.1 Create Expense (Equal Split)
* **Endpoint:** `POST /api/v1/expenses/`
* **Request Body:**
  ```json
  {
    "title": "Groceries",
    "amount": "1500.00",
    "group": 12,
    "category": "FOOD",
    "date": "2026-07-19",
    "paid_by": 5,
    "split_type": "EQUAL",
    "split_data": []
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "id": 45,
    "title": "Groceries",
    "amount": "1500.00",
    "group": 12,
    "category": "FOOD",
    "date": "2026-07-19",
    "paid_by": 5,
    "split_type": "EQUAL",
    "splits": [
      { "user": 5, "amount_owed": "500.00" },
      { "user": 6, "amount_owed": "500.00" },
      { "user": 7, "amount_owed": "500.00" }
    ]
  }
  ```

### 3.2 Create Expense (Itemised Split)
* **Endpoint:** `POST /api/v1/expenses/`
* **Request Body:**
  ```json
  {
    "title": "Dinner Bill",
    "amount": "900.00",
    "group": 12,
    "category": "FOOD",
    "date": "2026-07-19",
    "paid_by": 5,
    "split_type": "ITEM",
    "split_data": [
      { "name": "Pizza", "amount": 600.00, "user_ids": [5, 6] },
      { "name": "Cola", "amount": 300.00, "user_ids": [7] }
    ]
  }
  ```

---

## 🤝 4. Suggested Settlements & Confirms

### 4.1 Fetch suggested settlements (Debt Simplification)
* **Endpoint:** `GET /api/v1/groups/12/suggested-settlements/`
* **Response (200 OK):**
  ```json
  {
    "suggested_payments": [
      {
        "from_user_id": 6,
        "from_user": "bob456",
        "to_user_id": 5,
        "to_user": "alice123",
        "amount": "500.00"
      }
    ]
  }
  ```

### 4.2 Record a Settlement
* **Endpoint:** `POST /api/v1/settlements/`
* **Request Body:**
  ```json
  {
    "group": 12,
    "payer": 6,
    "receiver": 5,
    "amount": "500.00",
    "currency": "INR"
  }
  ```
* **Response (210 Created - Pending Status):**
  ```json
  {
    "id": 89,
    "group": 12,
    "payer": 6,
    "receiver": 5,
    "amount": "500.00",
    "status": "PENDING"
  }
  ```

### 4.3 Confirm Settlement (Receiver Action Only)
* **Endpoint:** `POST /api/v1/settlements/89/confirm/`
* **Response (200 OK):**
  ```json
  {
    "status": "confirmed",
    "message": "Settlement confirmed successfully."
  }
  ```
* **Note:** This updates `payer` reliability score in the background.

---

## 📊 5. Analytics & Budgeting

### 5.1 Fetch Budget vs Actual Status
* **Endpoint:** `GET /api/v1/analytics/budget/?group_id=12`
* **Response (200 OK):**
  ```json
  [
    {
      "category": "FOOD",
      "budget_limit": "5000.00",
      "actual_spent": "1000.00",
      "remaining": "4000.00",
      "percentage_used": "20.00",
      "over_budget": false,
      "budget_id": 3
    }
  ]
  ```

### 5.2 Set Monthly Budget
* **Endpoint:** `POST /api/v1/budgets/`
* **Request Body:**
  ```json
  {
    "category": "FOOD",
    "amount_limit": 5000.00,
    "month": 7,
    "year": 2026,
    "group": 12
  }
  ```
