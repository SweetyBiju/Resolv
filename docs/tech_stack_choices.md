# Resolv — Technology Stack Decisions

This document details the choices behind **Resolv's** technology stack and compares each selection against its common industry alternatives.

---

## 🐍 1. Backend: Python & Django REST Framework (DRF)
**Why Chosen:**
* **Batteries-Included Security & ORM:** Django provides out-of-the-box SQL injection protection, CSRF tokens, secure cookie handling, and a powerful Object-Relational Mapper (ORM) that handles complex transactions natively.
* **DRF Serialization:** Django REST Framework makes validating incoming payloads, managing nested relationships (like Expense splits), and enforcing model-level constraints clean and standardized.
* **Decimal Handling:** Python's native `decimal.Decimal` module coupled with Django's `DecimalField` makes handling penny-perfect monetary math simple, avoiding Javascript/JSON binary float conversion errors.

### 🆚 Alternatives Considered:
* **Node.js (Express/NestJS) vs Django:** Node is fast, but it lacks a built-in, cohesive ORM like Django's. Writing custom SQL schemas, handling migrations, and building auth loops in Express requires stitching together multiple third-party libraries (e.g. Prisma, Passport), which increases security risks.
* **FastAPI vs Django:** FastAPI is highly performant for asynchronous API calls. However, for a database-heavy CRUD application with complex transaction queries (like group balances and database constraints), Django's mature database ecosystem, migration system, and built-in Admin panel save months of development time.

---

## 🗄️ 2. Database: PostgreSQL (with SQLite for Development)
**Why Chosen:**
* **ACID Compliance & Transactions:** Expense splitting requires strict relational transactions. When an expense is added, the splits must be written atomically. If any split fails, the entire transaction must roll back. Relational databases excel at this.
* **Structural Check Constraints:** Allows database-level enforcement of business rules (e.g., `CHECK (amount > 0)` or `CHECK (payer_id != receiver_id)`), ensuring mathematical security even if application code fails.

### 🆚 Alternatives Considered:
* **MongoDB (NoSQL) vs PostgreSQL:** NoSQL databases (like MongoDB) do not natively enforce relations or cross-document consistency checks easily. A document-based store would allow users to store splits inside a parent expense document, but running complex joins (e.g. summarizing a user's net debt across 10 different groups and 50 different expenses) is slow and highly prone to race conditions and balance discrepancies.

---

## 🎨 3. Frontend: Vanilla HTML5, CSS3, and ES6 JavaScript Modules
**Why Chosen:**
* **Zero Build Steps:** The frontend runs directly in any modern browser without needing `npm run build`, Webpack, Babel, Vite, or Node configuration. It is lightweight, fast, and easy to deploy statically.
* **Control Over Script Caching:** Simple version query parameters (`?v=2`) can bust browser script caching without relying on complex chunk hashing algorithms.
* **Performance:** There is no framework overhead or heavy JavaScript bundle size, allowing the UI to load instantly.

### 🆚 Alternatives Considered:
* **React / Next.js / Vite vs Vanilla JS:** Frameworks like React introduce a build-step requirement, node modules overhead, and state-management complexity (Redux, Zustand) that is unnecessary for a static single-page app architecture. Vanilla ES Modules are now natively supported in all modern browsers, making state sharing and module imports standard.
* **Tailwind CSS vs Vanilla CSS:** Tailwind requires a CSS compilation process (PostCSS/Tailwind CLI) and clutters the HTML markup. Plain Vanilla CSS with custom properties (CSS variables) allows rich themes, HSL color palettes, responsive layouts, and animations without build-step compile constraints.
