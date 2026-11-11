# PARALLAXAI — AI GOVERNANCE COMMAND CENTER (`frontend-web/`)

Enterprise React + TypeScript + Vite frontend for **ParallaxAI**, the Human-AI Co-Governance Platform.

---

## 1. Folder Structure

```text
frontend-web/
├── .env.example
├── .prettierrc
├── components.json
├── eslint.config.js
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.app.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
└── src/
    ├── main.tsx
    ├── app/
    │   ├── App.tsx
    │   ├── providers.tsx
    │   ├── query-client.ts
    │   └── router.tsx
    ├── components/
    │   ├── common/
    │   │   ├── data-table.tsx
    │   │   ├── module-placeholder.tsx
    │   │   ├── page-header.tsx
    │   │   ├── search-input.tsx
    │   │   ├── stat-card.tsx
    │   │   └── status-badge.tsx
    │   ├── feedback/
    │   │   ├── confirm-dialog.tsx
    │   │   ├── empty-state.tsx
    │   │   ├── error-boundary.tsx
    │   │   ├── error-state.tsx
    │   │   ├── loading-skeleton.tsx
    │   │   └── toast-viewport.tsx
    │   ├── layout/
    │   │   └── contextual-right-panel.tsx
    │   ├── navigation/
    │   │   ├── app-sidebar.tsx
    │   │   ├── app-topbar.tsx
    │   │   ├── permission-guard.tsx
    │   │   └── protected-route.tsx
    │   └── ui/
    │       ├── badge.tsx
    │       ├── button.tsx
    │       ├── card.tsx
    │       ├── dialog.tsx
    │       ├── input.tsx
    │       └── skeleton.tsx
    ├── features/
    │   ├── auth/
    │   │   └── auth-placeholders.tsx
    │   └── common/
    │       ├── feature-placeholders.tsx
    │       └── system-pages.tsx
    ├── layouts/
    │   └── app-shell-layout.tsx
    ├── lib/
    │   ├── api-config.ts
    │   ├── navigation-config.ts
    │   └── utils.ts
    ├── services/
    │   ├── api-client.ts
    │   ├── api-error.ts
    │   └── auth-service.ts
    ├── stores/
    │   ├── auth-store.ts
    │   └── ui-store.ts
    ├── styles/
    │   └── globals.css
    ├── test/
    │   ├── api-client.test.ts
    │   ├── app-shell.test.tsx
    │   ├── routing.test.tsx
    │   └── setup.ts
    └── types/
        ├── auth.ts
        ├── governance.ts
        └── navigation.ts
```

---

## 2. Dependencies

- **Core**: `react`, `react-dom`, `typescript`, `vite`, `tailwindcss`
- **UI Primitives & Icons**: `@radix-ui/react-dialog`, `@radix-ui/react-slot`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`
- **Routing**: `react-router-dom`
- **Server State**: `@tanstack/react-query`
- **Client State**: `zustand`
- **Visualization**: `recharts`, `@xyflow/react`
- **Forms & Validation**: `react-hook-form`, `@hookform/resolvers`, `zod`
- **HTTP Client**: `axios`
- **Testing & Quality**: `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `eslint`, `prettier`

---

## 3. Design System (`PARALLAXAI — Dark Enterprise Intelligence`)

Defined in `src/styles/globals.css` and `tailwind.config.js`:
- **Main Background**: Deep navy / charcoal (`220 35% 7%`)
- **Sidebar Background**: Darker navy (`222 40% 5%`)
- **Card Surface**: Subtle elevated surface (`221 36% 10%`)
- **Primary Accent**: Electric Cyan (`189 94% 43%`)
- **Secondary Accent**: Governance Violet (`262 83% 64%`)
- **Semantic Status Colors**: Muted green (`--success`), Amber (`--warning`), Red (`--destructive`), Informational Blue (`--info`)
- **Typography**: `Inter` / `Geist` for UI hierarchy, `JetBrains Mono` for IDs, hashes, and metrics.

---

## 4. Environment Variables

Copy `.env.example` to `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_APP_ENV=development
```

Never place secrets in `VITE_*` variables.

---

## 5. Development Commands

```bash
npm run dev        # Start Vite dev server on http://localhost:5173
npm run typecheck  # Run strict TypeScript compiler checks
npm run lint       # Run ESLint across src/
npm run test       # Run Vitest unit & component test suites
npm run build      # Build production bundle in dist/
npm run preview    # Preview production bundle
```

---

## 6. Routing & Permission Architecture

- Public routes: `/login`, `/register`, `/forgot-password`
- Protected application routes under `/app/*`:
  - `/app/dashboard` (`decisions:read`)
  - `/app/decisions` & `/app/decisions/:decisionId` (`decisions:read`)
  - `/app/agents` & `/app/agents/:agentId` (`agents:read`)
  - `/app/voting` (`voting:read`)
  - `/app/influence` (`agents:read`)
  - `/app/bias` (`bias:read`)
  - `/app/governance` (`governance:read`)
  - `/app/audit` (`audit:read`)
  - `/app/notifications` (`notifications:read`)
  - `/app/users` (`users:read` or `roles:manage`)
  - `/app/roles` (`roles:manage`)
  - `/app/settings` (`system:configure`)
  - `/app/unauthorized` & `*` (`NotFoundPage`)

---

## 7. API Client & Authentication Integration

- `src/services/api-client.ts` configures Axios with `baseURL: VITE_API_BASE_URL` and `withCredentials: true` (for the `HttpOnly` `parallaxai_refresh_token` cookie).
- Short-lived JWT access tokens are kept strictly in memory (`useAuthStore`) and attached via `Authorization: Bearer <token>`.
- Concurrent `401 Unauthorized` responses share a single in-flight `POST /api/v1/auth/refresh` request, retry once with the rotated token, and clear the session if refresh fails.

---

## 8. Known Limitations (Phase 6 Scope)

- Feature modules currently render honest architecture placeholders (`ModulePlaceholder`) rather than fabricated metrics.
- Full interactive authentication forms (`Login`, `Register`, `Forgot Password`, honest `Google OAuth` button) will be implemented in **Phase 7**.
- Live dashboard charts, decision workspace, agent registry, voting, influence graph, bias scanner, governance console, audit logs, notifications, users/roles, settings, and WebSocket event streams will be connected in **Phases 8–11**.

