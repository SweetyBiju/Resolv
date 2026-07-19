# ⚖️ Resolv — Collaborative Expense Splitting & Debt Simplification

**Resolv** is a production-ready, collaborative expense-sharing web application engineered to remove the friction and complexity from group finances. By utilising advanced pairwise debt minimization algorithms, a secure verification loop for settlements, category budgeting, and transaction auditing, Resolv provides a premium, transparent experience for splitting bills.

---

## 🚀 Key Features

* **Pairwise Debt Simplification:** Automatically simplifies circular debts down to the absolute minimum number of peer-to-peer transfers (reducing transactions from $O(N^2)$ to $O(N)$).
* **Flexible Split Algorithms:** Supports **Equal**, **Exact**, **Percent**, and **Itemized (By Item)** split types with a native floating-point rounding remainder guard to guarantee penny-perfect balances.
* **Double-Verification Settlement Loop:** Payments are registered in a `PENDING` state and must be confirmed by the receiving user before updating balances, preventing settlement fraud.
* **Gamified Reliability Ratings:** Tracks a public user reliability score (starting at `70.00` and capped at `100.00`) which increments on successful settlements and decreases on defaults.
* **Audit Logs:** Tracks every event (group creations, updates, expense deletions, and confirms) and translates them into plain-English timeline logs on the dashboard.
* **Category Budgeting:** Configure category-specific monthly spending caps with progress bars that turn red if category spending is exceeded.
* **Export Data:** Download complete group spending audit trails to CSV files.

---

## 🛠️ Technology Stack

* **Backend:** Python 3.13 + Django 6.0 + Django REST Framework (DRF) + SQLite (Dev) / PostgreSQL (Prod)
* **Frontend:** Vanilla HTML5 + CSS3 (Modern HSL system, variables, custom responsive grid) + ES6 Javascript Modules
* **Test Suite:** Pytest + Django-pytest

---

## 📂 Project Architecture

```
Resolv/
├── backend/                       ← Django Project Root
│   ├── core/                      ← Settings, URL routing, configurations
│   ├── activity/                  ← Audit log and timeline streams
│   ├── analytics/                 ← Spending trends, insights, and budgeting
│   ├── expenses/                  ← Expense models, split algorithms, settlements
│   ├── groups/                    ← Group lifecycle, invites, and roster management
│   └── users/                     ← Auth models, profiles, and reliability metrics
│
├── frontend/                      ← Vanilla Static Web Client
│   ├── css/                       ← Styling systems (tokens, inputs, layouts)
│   ├── js/                        
│   │   ├── components/            ← Shared UI elements (sidebar, toast, nav)
│   │   ├── core/                  ← API wrappers, Auth state, utility functions
│   │   └── pages/                 ← Page-specific controller JS files
│   └── *.html                     ← Single Page Views
│
└── docs/                          ← Comprehensive Documentation
```

---

## ⚙️ Quick Start & Local Setup

### 1. Prerequisites
* Python 3.13+ installed on your system.

### 2. Backend Setup
1. Open a terminal in the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\activate

   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations and start the Django development server:
   ```bash
   python manage.py migrate
   python manage.py runserver 8000
   ```
   The backend API is now running at: `http://localhost:8000`

### 3. Frontend Setup
Because Resolv is built using modern vanilla ES Modules, it can be served using any simple HTTP server:
1. Open a new terminal in the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Start a simple web server:
   ```bash
   # Using Python
   python -m http.server 3000
   ```
3. Open your browser and navigate to: `http://localhost:3000`

---

## 🧪 Running the Test Suite
The backend contains a comprehensive unit and integration test suite (covering Auth, Split math, Debt simplification, Reliability score updates, and deletion guards).

To run the tests:
1. Navigate to the `backend/` directory and ensure your virtual environment is active.
2. Run pytest:
   ```bash
   pytest
   ```

---

## 📝 Additional Documentation
For complete technical guides, refer to the files in the `docs/` directory:
* 🗺️ **[API Workflow Guide](file:///c:/Users/hp/OneDrive/Desktop/Resolv/docs/api_workflow.md):** Complete payload contracts and endpoints.
* 🏗️ **[Architecture Details](file:///c:/Users/hp/OneDrive/Desktop/Resolv/docs/architecture_details.md):** Detailed database schemas, models, and constraints.
* 🏃‍♂️ **[User Flow Journey](file:///c:/Users/hp/OneDrive/Desktop/Resolv/docs/user_flow.md):** Step-by-step UI maps and user states.
* 🧮 **[Debt Simplification Algorithm](file:///c:/Users/hp/OneDrive/Desktop/Resolv/docs/debt_simplification.md):** Plain explanation of pairwise debt minimization math.
* 💎 **[Features Checklist](file:///c:/Users/hp/OneDrive/Desktop/Resolv/docs/features_and_functionalities.md):** List of support features.
* 🛡️ **[Tech Stack Decisions](file:///c:/Users/hp/OneDrive/Desktop/Resolv/docs/tech_stack_choices.md):** Rationales behind choosing Django, PostgreSQL, and Vanilla Javascript.
