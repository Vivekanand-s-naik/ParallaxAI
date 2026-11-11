# PARALLAXAI — Human-AI Co-Governance Platform

**PARALLAXAI — AI GOVERNANCE COMMAND CENTER** is an enterprise Human-AI Co-Governance Platform enabling collaborative decision-making between multi-provider AI agents and human operators with real-time fairness monitoring, declarative YAML policy enforcement, weighted consensus calculation, and SHA-256 tamper-evident audit trails.

---

## 1. Architecture Overview

- **Frontend (`frontend-web/`)**: React 18, TypeScript 5.6 (strict mode), Vite 6, Tailwind CSS, customized Radix/shadcn UI primitives, TanStack Query v5, Zustand v5, React Router v6, Recharts, `@xyflow/react` (interactive agent influence graphs), React Hook Form + Zod, Axios with single-flight JWT refresh rotation, and Vitest + React Testing Library.
- **Backend (`backend/`)**: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16, Redis 7, Argon2id (`argon2-cffi`) password hashing, JWT access tokens + HttpOnly refresh token rotation with family reuse detection, granular database-backed RBAC (6 roles, 19 permissions), Scikit-learn ML Bias & Fairness Scanner (`IsolationForest` + `RandomForest`), multi-provider AI integration (`OpenAI`, `Anthropic`, `Google Gemini` + deterministic fallback), and real-time WebSocket event broadcasting (`/ws`).
- **Legacy Streamlit (`main.py`, `frontend/`)**: Preserved untouched alongside the modern React application in `frontend-web/`.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Role | Description | Key Permissions |
| :--- | :--- | :--- |
| `SUPER_ADMIN` | Full platform & RBAC control | All 19 permissions including `roles:manage`, `users:manage`, `system:configure` |
| `ADMIN` | Platform & user administration | All 18 operational permissions except `roles:manage` |
| `GOVERNANCE_OFFICER` | Policy & decision resolution | `decisions:read/create/update/approve/reject/escalate`, `governance:read/manage`, `voting:participate`, `audit:read` |
| `HUMAN_REVIEWER` | Domain voting & escalation | `decisions:read/escalate`, `voting:read/participate`, `bias:read`, `audit:read` |
| `ANALYST` | Case creation & analysis | `decisions:read/create/update`, `agents:read`, `voting:read`, `bias:read`, `audit:read` |
| `VIEWER` | Default self-registration role | `decisions:read`, `agents:read`, `voting:read`, `governance:read`, `bias:read`, `notifications:read` |

---

## 3. Seeded Demo Accounts (Development Environment)

- **Super Admin**: `admin@parallaxai.io` / `admin123` (`SUPER_ADMIN`)
- **Governance Officer**: `sarah.chen@parallaxai.io` / `governance123` (`GOVERNANCE_OFFICER`)
- **Human Reviewer**: `reviewer@parallaxai.io` / `reviewer123` (`HUMAN_REVIEWER`)
- **Risk Analyst**: `analyst@parallaxai.io` / `analyst123` (`ANALYST`)

---

## 4. Local Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (`uv` recommended)
- Node.js 20+ & npm

### Step 1: Start PostgreSQL & Redis
```bash
docker compose up -d postgres redis
```

### Step 2: Run Database Migrations & Idempotent Seed
```bash
uv run alembic upgrade head
uv run python -m backend.database.seed
```

### Step 3: Start the FastAPI Backend
```bash
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Start the React Command Center (`frontend-web/`)
```bash
cd frontend-web
npm install
npm run dev
```

---

## 5. Verification & Test Suites

### Backend Test Suite (Pytest)
```bash
uv run pytest -v
```

### Frontend Verification Suite (TypeScript, ESLint, Vitest, Production Build)
```bash
cd frontend-web
npm run typecheck
npm run lint
npm run test
npm run build
```

