# Neurex Frontend

Frontend for the Enterprise Knowledge Intelligence Platform — React 19, TypeScript, Vite, Tailwind CSS v4.

## Stack

- **React 19 + TypeScript** — strict mode, no `any`
- **Vite** — dev server and build
- **Tailwind CSS v4** — CSS-first theme tokens in `src/index.css`, light/dark via `.dark` class
- **React Router v7** (data router) — route-level code splitting via `lazy`
- **TanStack Query** — server state, caching, mutations
- **Zustand** — client state only (`stores/authStore.ts`, `stores/themeStore.ts`, `stores/uiStore.ts`)
- **React Hook Form + Zod** — forms and validation
- **class-variance-authority + tailwind-merge** — component variants
- **Motion** — enter/exit transitions (dialogs, dropdowns, tooltips)
- **Vitest + React Testing Library** — unit/component tests
- **Playwright** — e2e tests

## Getting started

```bash
npm install
cp .env.example .env   # set VITE_API_URL to your backend
npm run dev
```

## Scripts

| Script                            | Purpose                                              |
| --------------------------------- | ---------------------------------------------------- |
| `npm run dev`                     | Start the Vite dev server                            |
| `npm run build`                   | Type-check (`tsc -b`) then production build          |
| `npm run preview`                 | Serve the production build locally                   |
| `npm run lint`                    | ESLint (type-checked rules)                          |
| `npm run format` / `format:check` | Prettier                                             |
| `npm run typecheck`               | `tsc -b` only                                        |
| `npm run test`                    | Vitest unit/component tests                          |
| `npm run test:watch`              | Vitest in watch mode                                 |
| `npm run test:e2e`                | Playwright e2e tests (builds + serves the app first) |

## Project structure

```
src/
├── app/            App shell entry: App.tsx, router.tsx, providers.tsx, ErrorBoundary.tsx
├── components/
│   ├── ui/         Design-system primitives (Button, Dialog, Table, ...)
│   ├── layout/     AppShell, Sidebar, Topbar, AuthLayout, ...
│   ├── chat/        Chat UI
│   └── citations/   Citation chips + source preview
├── features/       Business logic by domain: api.ts, hooks.ts, schemas.ts,
│                    types.ts, components/ (authentication, document-management,
│                    ingestion-monitoring, search, conversations, evaluations, settings)
├── pages/          Route-level page components
├── services/
│   ├── api/         apiClient, ApiError, shared request types
│   └── streaming/    Chat SSE streaming
├── stores/         Zustand stores (client state only)
├── hooks/          Cross-feature hooks (useDebouncedValue, ...)
├── types/          Shared API envelope types
└── utils/          cn, format, highlight
```

## Backend contract

No backend exists yet in this repo. Every `features/*/api.ts` file targets a REST path
(`/documents`, `/search`, `/chat/messages`, `/evaluations/...`, `/settings`, ...) that a
future FastAPI service is expected to implement — see the comment at the top of each
`api.ts`. Until then, every data-driven page correctly shows its error state (network
requests to `VITE_API_URL` fail) rather than crashing.

## Environment variables

| Variable       | Required | Description                 |
| -------------- | -------- | --------------------------- |
| `VITE_API_URL` | Yes      | Base URL of the backend API |

`VITE_*` variables are bundled into the client and are public — never put secrets here.
