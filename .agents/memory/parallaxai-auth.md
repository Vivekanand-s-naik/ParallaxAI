---
name: ParallaxAI auth system
description: How authentication works in ParallaxAI — tokens, users, frontend gate
---

## Auth design
- Tokens: HMAC-SHA256 signed, 24h TTL, using SESSION_SECRET env var (Replit secret)
- Login: POST /api/auth/login → returns `{token, user}`
- All API endpoints require Bearer token except /health and /api/auth/*
- Admin-only actions (create/delete rules, delete decisions) use `require_admin` dependency

## Users (in-memory, backend/auth.py)
- admin / admin123 → role: admin
- analyst / analyst123 → role: analyst
- reviewer / reviewer123 → role: reviewer

## Frontend
- frontend/auth.py: login form, show_login_page(), is_authenticated(), get_auth_headers(), logout()
- frontend/api_client.py: wraps requests with Bearer token from session_state
- main.py: checks is_authenticated() before rendering any page; unauthenticated users see login only

**Why:** No auth layer existed; all endpoints were open. SESSION_SECRET is already set as a Replit secret.

**How to apply:** Any new API endpoint should use `Depends(get_current_user)` or `Depends(require_admin)`. Frontend calls should use `frontend.api_client` (api.get/post/put/delete).
