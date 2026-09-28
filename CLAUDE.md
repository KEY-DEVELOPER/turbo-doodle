# EdgeLedger — Agent Instructions

You are one of several AI agents building EdgeLedger in parallel, each in its own git worktree.
Read this file fully before starting any task. When this file and your task prompt conflict, ask.

## 1. What we are building

EdgeLedger is a football (soccer) +EV **research, decision-support and tracking** web app.
It does not place bets, hold money or store bookmaker passwords.

- **Source of truth:** `tasks/prd-edgeledger-ev-research-suite.md`. Requirements have IDs
  (e.g. `DATA-02`, `LED-01`, `PATO-01`) and acceptance criteria (AC). Always read the section
  for your requirement ID before writing code.
- **MVP scope:** pre-match, regulation-time (90' + stoppage) 1X2 only. Totals, BTTS, AH,
  in-play, accumulators, arbitrage and other sports are out of scope unless the task says so.
- **"No qualifying opportunities" is a normal, designed state.** Never tune code or thresholds
  to make opportunities appear.

## 2. Stack (PRD §14.1) — do not change without an approved decision in `docs/decisions/`

| Layer | Choice |
|---|---|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 (modular monolith) |
| Workers | Dramatiq on Redis; one APScheduler process that only enqueues jobs |
| Database | PostgreSQL 16, monthly partitions for `odds_snapshot`, `opportunity_evaluation`, `audit_log` |
| Analytics store | Parquet in S3-compatible storage (MinIO locally), queried with DuckDB |
| Modelling | NumPy, SciPy, statsmodels, scikit-learn |
| Frontend | Next.js + TypeScript, TanStack Query, Radix primitives, ECharts |
| Admin | SQLAdmin for curation screens |
| API client | Generated from OpenAPI — never hand-edit generated files |

## 3. Repository layout

```
backend/
  app/
    sources/  reference/  events/  markets/  features/  models/
    opportunities/  pato/  betting/  ledger/  settlement/  analytics/
    notify/  wellbeing/  identity/  audit/
    core/          # shared: db session, ULIDs, time utils, bitemporal helpers, errors
    api/v1/        # routers only; business logic lives in modules
  migrations/      # Alembic
  tests/
frontend/
tests/e2e/
docs/decisions/    # ADRs and meeting outputs
tasks/             # PRD and task specs
```

## 4. Module ownership (PRD §14.3) — the most important rule

Each agent owns specific modules. **Only edit files inside the modules your task names.**
If you need a change in another module, stop and say so in your final message (or ask the
human); do not make the change yourself. `backend/app/core/` changes need the Architect.

Module boundaries are enforced by import-linter. Key rules:
- `sources` never writes curated tables directly.
- `markets` knows nothing about users.
- `features` / `models` never read user data.
- `opportunities` never writes bets.
- `pato` never feeds models unless a cohort is flagged validated.
- `betting` never modifies predictions or quotes.
- `ledger` is append-only; `settlement` always goes through `ledger`.
- `notify` never sends without a `wellbeing` check.
- `audit` entries are never deleted.

## 5. Non-negotiable data rules

- **Odds:** stored only as decimal (`NUMERIC(8,3)`). Other formats are display-only.
- **Money:** `NUMERIC(18,4)` / Python `Decimal`. Never floats for money or odds.
- **Time:** store UTC, microsecond precision. Keep `event_time`, `source_time`, `observed_at`,
  `ingested_at`, `valid_from/valid_to`, `generated_at`/`as_of` distinct (PRD §5.4).
- **IDs:** internal ULIDs. External IDs live only in `source_entity_map`.
- **Append-only:** raw payloads, odds snapshots, predictions, opportunity evaluations,
  signals, bets' price/snapshot fields, ledger entries, audit log. Corrections are new rows
  (bitemporal close + insert, or reversal + repost). Never `UPDATE` history.
- **Idempotency:** every ingest, settlement and write endpoint must be safe to replay
  (unique keys / `Idempotency-Key` header).
- **Contracts:** quotes are comparable only if `contract_signature` is equal (PRD §5.3).
- **Never** build a no-margin benchmark from best prices across different bookmakers
  (error `SYNTHETIC_MARKET_NOT_ALLOWED`).
- **Paper and actual** bets/ledgers are never summed together anywhere.

## 6. Data sources and licensing (PRD §4)

- Allowed: licensed APIs only (Sportmonks, The Odds API, football-data.org), via connectors
  registered in the licence register (`source` table) with permitted-use flags.
- **Forbidden:** scraping or calling undocumented endpoints of Sofascore, FotMob, Flashscore,
  FBref, WhoScored, Understat, Transfermarkt, or any site. Do not use Football-Data.co.uk CSVs.
  Do not bypass rate limits, CAPTCHAs, logins or geo-blocks.
- Data with `permitted_train = false` must never enter a training dataset.
- Until real API keys exist, use **recorded fixtures** in `backend/tests/fixtures/` — never
  invent a live integration against a real endpoint in tests.
- API keys come from environment variables (`.env`, never committed). Never print, log or
  commit secrets. Never send provider keys to the browser.

## 7. Modelling and research integrity (PRD §6–8, §11)

- No feature may use information with `valid_from > as_of` (point-in-time). Leakage tests
  must stay green; never weaken or skip them.
- Splits are chronological and grouped by event. Do not touch the locked test period unless
  the task explicitly says "final evaluation".
- Probabilities for mutually exclusive outcomes must sum to 1 (± 1e-9).
- Report log loss, Brier and RPS — never accuracy or win rate alone.
- Log every backtest run in `experiment_run`, including failed or abandoned variants.
- Probability edge (pp) and EV (% of stake) are different numbers; always label both.
- If results look too good, assume a bug or leakage and investigate before reporting.

## 8. Product copy and responsible use (PRD §13.7, §15)

- **Banned words** in UI strings, alerts, emails and docs aimed at users: "guaranteed", "lock",
  "risk-free", "sure bet", "can't lose", "free money", "banker", "certain", "easy profit"
  (and equivalents in Italian). CI runs a linter (RG-08).
- No urgency: no countdowns, "last chance", streaks, volume badges or celebratory win animations.
- Never suggest lowering thresholds, increasing stakes, or recovering losses.
- Use the labels "estimated", "model", "benchmark", "observed".
- Status is never shown by colour alone (text + icon + colour). Target WCAG 2.2 AA.
- Cooling-off / self-exclusion must disable scanner, alerts and recording actual bets.

## 9. How to work on a task

1. Read the task prompt, then the PRD section(s) for its requirement ID(s).
2. Write the acceptance criteria as tests first (`test_<REQ-ID>_...`), then implement.
3. Keep the change scoped to your module(s) and to the requirement. No drive-by refactors.
4. Run before finishing:
   ```bash
   cd backend && ruff check . && ruff format --check . && mypy app && pytest -q
   lint-imports
   cd ../frontend && npm run lint && npm run typecheck && npm test
   ```
   (Run only the parts relevant to your change if the other side does not exist yet.)
5. Commit with a message like `LED-01: double-entry ledger accounts and transactions`.
6. End your turn with a short summary: requirement IDs done, ACs covered by which tests,
   anything left undone, and any change needed in a module you do not own.

## 10. Database migrations

- At most **one Alembic migration per PR**, named `<rev>_<req_id>_<short_desc>.py`.
- Before opening a PR: `git fetch && git rebase origin/main`, then check `alembic heads`.
  If there is more than one head, regenerate your migration on top of the current head
  (do not create merge migrations unless asked).
- Migrations must be reversible (`downgrade` implemented) unless the task says otherwise.
- User-owned tables get `user_id` and a row-level security policy.

## 11. Pull requests

- Title: `<REQ-ID>: <what>`. Body: requirement IDs, AC checklist with test names, notes on
  anything out of scope. Add `Closes #<issue>` when there is an issue.
- CI must be green. Do not disable, skip or delete tests to make CI pass.
- Do not merge your own PR unless the task explicitly says to.

## 12. When unsure

Ask a question rather than guess — especially about: licensing, settlement rules, anything
touching money or the ledger, cross-module changes, or changing a PRD default.
Open decisions are listed in PRD §20; do not decide them silently in code.
