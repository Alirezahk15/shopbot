# Web Admin Panel — FastAPI + React

## Overview

A modern web-based admin panel for the Telegram shop bot, built with:
- **Backend:** FastAPI (Python) — shares the same `database.py` and `shop.db`
- **Frontend:** React + Vite + TailwindCSS
- **Auth:** JWT tokens (stateless, no session storage needed)
- **Communication:** REST API with JSON

---

## Architecture

```mermaid
graph TD
    A[Admin Browser] -->|HTTPS :3000| B[React Frontend]
    B -->|REST API calls| C[FastAPI Backend :8000]
    C --> D[(shop.db SQLite)]
    E[Telegram Bot] --> D
    C -->|JWT Auth| F[/api/auth/login]
    B -->|localStorage JWT| G[Protected Routes]
```

---

## Project Structure

```
my bot/
├── main.py              (Telegram bot — existing)
├── database.py          (shared DB layer — existing)
├── config.py            (shared config — existing)
├── shop.db              (SQLite database — existing)
│
├── api/                 (FastAPI backend — NEW)
│   ├── main.py          (FastAPI app, CORS, startup)
│   ├── auth.py          (JWT login/logout)
│   ├── routers/
│   │   ├── dashboard.py (stats endpoint)
│   │   ├── users.py     (user CRUD)
│   │   ├── products.py  (product/category/stock CRUD)
│   │   ├── orders.py    (order list/detail)
│   │   ├── payments.py  (card payment approve/reject)
│   │   ├── tickets.py   (ticket list/reply/close)
│   │   ├── settings.py  (feature toggles, card/wallet)
│   │   └── broadcast.py (send message to all users)
│   └── requirements.txt (fastapi, uvicorn, python-jose, passlib)
│
├── panel/               (React frontend — NEW)
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   └── client.js    (axios instance with JWT interceptor)
│       ├── pages/
│       │   ├── Login.jsx
│       │   ├── Dashboard.jsx
│       │   ├── Users.jsx
│       │   ├── Products.jsx
│       │   ├── Orders.jsx
│       │   ├── Payments.jsx
│       │   ├── Tickets.jsx
│       │   └── Settings.jsx
│       └── components/
│           ├── Sidebar.jsx
│           ├── StatCard.jsx
│           ├── DataTable.jsx
│           └── ConfirmModal.jsx
│
├── install.sh           (Linux/Mac easy install — NEW)
├── install.bat          (Windows easy install — NEW)
└── start.bat / start.sh (run bot + panel together — NEW)
```

---

## Backend — FastAPI (`api/`)

### Authentication

- Single admin password stored in `.env` as `PANEL_PASSWORD`
- Login returns a **JWT token** (expires in 24h)
- All API routes require `Authorization: Bearer <token>` header

```python
# api/auth.py
POST /api/auth/login   { "password": "..." }  → { "token": "..." }
POST /api/auth/logout  (client just deletes token)
GET  /api/auth/me      → { "valid": true }
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard` | Stats: users, orders, revenue, pending items |
| GET | `/api/users` | Paginated user list |
| GET | `/api/users/{uid}` | User detail + orders + stats |
| POST | `/api/users/{uid}/balance` | Add/subtract balance |
| POST | `/api/users/{uid}/block` | Toggle block status |
| GET | `/api/products` | All products with stock count |
| POST | `/api/products` | Add product |
| PUT | `/api/products/{pid}` | Edit product |
| DELETE | `/api/products/{pid}` | Delete product |
| POST | `/api/products/{pid}/stock` | Add stock items |
| GET | `/api/orders` | Paginated orders |
| GET | `/api/orders/{oid}` | Order detail |
| GET | `/api/payments/pending` | Pending card payments |
| POST | `/api/payments/{id}/approve` | Approve card payment |
| POST | `/api/payments/{id}/reject` | Reject card payment |
| GET | `/api/tickets` | Open tickets |
| POST | `/api/tickets/{id}/reply` | Reply to ticket |
| POST | `/api/tickets/{id}/close` | Close ticket |
| GET | `/api/settings` | All feature flags + config |
| POST | `/api/settings` | Update a setting |
| POST | `/api/broadcast` | Send message to all users |

### Key Design Decisions

1. **Shared `database.py`** — FastAPI imports the same `database.py` directly. No ORM needed.
2. **SQLite WAL mode** — Enable `PRAGMA journal_mode=WAL` in `database.py` to allow concurrent reads from bot + panel.
3. **No WebSocket for now** — Dashboard stats refresh every 30s via polling. Can add WebSocket later.
4. **CORS** — Allow `http://localhost:3000` in dev, configurable for production.

---

## Frontend — React (`panel/`)

### Tech Stack

| Tool | Purpose |
|------|---------|
| React 18 | UI framework |
| Vite | Build tool (fast dev server) |
| TailwindCSS | Styling |
| React Router v6 | Client-side routing |
| Axios | HTTP client |
| Recharts | Charts for dashboard |
| React Query | Data fetching + caching |

### Pages

#### Login (`/login`)
- Password input
- Calls `POST /api/auth/login`
- Stores JWT in `localStorage`
- Redirects to dashboard

#### Dashboard (`/`)
- Stat cards: Total Users, Total Orders, Revenue, Pending Payments, Open Tickets
- Line chart: Orders per day (last 7 days)
- Quick action buttons

#### Users (`/users`)
- Searchable, paginated table
- Columns: ID, Username, Balance, Orders, Joined, Status
- Actions: View detail, Add balance, Block/Unblock

#### Products (`/products`)
- Category tabs
- Product cards with stock count
- Add/Edit/Delete product modal
- Add stock (textarea, one item per line)

#### Orders (`/orders`)
- Filterable table (by date, user)
- Columns: ID, Product, User, Price, Date
- Click to view delivered content

#### Payments (`/payments`)
- Pending card payments with receipt image
- Approve / Reject buttons
- Auto-refresh every 30s

#### Tickets (`/tickets`)
- Open tickets list
- Click to view + reply inline
- Close ticket button

#### Settings (`/settings`)
- Feature toggles (on/off switches)
- Card number / card holder fields
- USDT wallet address field
- Save button

---

## Install Scripts

### `install.sh` (Linux/Mac)

```bash
#!/bin/bash
echo "Installing Telegram Shop Bot + Web Panel..."

# Python dependencies
pip install -r requirements.txt
pip install -r api/requirements.txt

# Node.js dependencies
cd panel && npm install && npm run build && cd ..

echo "Done! Run: python main.py & uvicorn api.main:app --port 8000"
```

### `install.bat` (Windows)

```bat
@echo off
echo Installing Telegram Shop Bot + Web Panel...

pip install -r requirements.txt
pip install -r api\requirements.txt

cd panel
npm install
npm run build
cd ..

echo Done! Run start.bat to launch everything.
```

### `start.bat` (Windows — run everything)

```bat
@echo off
start "Telegram Bot" python main.py
start "Web API" uvicorn api.main:app --port 8000
start "Web Panel" cmd /c "cd panel && npm run dev"
echo All services started!
echo Bot: running
echo API: http://localhost:8000
echo Panel: http://localhost:3000
```

---

## Security Considerations

1. **Panel password** stored in `.env` as `PANEL_PASSWORD` — never hardcoded
2. **JWT secret** stored in `.env` as `JWT_SECRET`
3. **CORS** restricted to known origins
4. **Rate limiting** on login endpoint (max 5 attempts/minute)
5. **HTTPS** required in production (use nginx reverse proxy)
6. **SQLite WAL mode** prevents write conflicts between bot and panel

---

## `.env` additions needed

```env
# Web Panel
PANEL_PASSWORD=your_strong_password_here
JWT_SECRET=your_random_jwt_secret_here
PANEL_PORT=8000
```

---

## Implementation Order

1. Set up FastAPI backend with auth + dashboard endpoint
2. Add all API routers (users, products, orders, payments, tickets, settings)
3. Enable SQLite WAL mode in `database.py`
4. Set up React + Vite + Tailwind project
5. Build Login page + JWT interceptor
6. Build Dashboard page
7. Build remaining pages (Users, Products, Orders, Payments, Tickets, Settings)
8. Write install scripts
9. Test end-to-end
