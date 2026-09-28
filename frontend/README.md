# EdgeLedger frontend

Next.js 16 (App Router) + TypeScript, TanStack Query, typed client via `openapi-fetch`.
See the root `README.md` → "Local development" for how to run it.

| Command | What it does |
|---|---|
| `npm run dev` | Dev server on http://localhost:3000 |
| `npm run lint` | ESLint (zero warnings allowed) |
| `npm run typecheck` | `next typegen` + `tsc --noEmit` |
| `npm test` | Vitest (jsdom) once; `npm run test:watch` to watch |
| `npm run gen:api` | Regenerate `src/lib/api/generated/schema.ts` from `openapi.json` |
| `npm run lint:copy` | RG-08 banned-terms linter over user-facing text |

Next.js 16 differs from older versions: read `node_modules/next/dist/docs/` before using an
API you have not checked (see `AGENTS.md`).
