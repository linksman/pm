# Kanban Studio

A full-stack project management app built as a Udemy course project. FastAPI backend serves a statically-built Next.js frontend from a single Docker container. AI chat sidebar lets users ask an LLM to update the Kanban board.

## Architecture

```
pm/
├── backend/          # FastAPI app (Python)
│   ├── main.py       # All API routes and DB logic
│   └── data/         # SQLite database (kanban.db, git-ignored)
├── frontend/         # Next.js app
│   ├── src/
│   │   ├── app/      # Next.js app router (page.tsx = login + board root)
│   │   ├── components/  # KanbanBoard, KanbanColumn, KanbanCard, ChatSidebar
│   │   └── lib/      # kanban.ts (types/helpers), api.ts (URL helper)
│   └── out/          # Static export (built by next build, copied to backend/static)
├── scripts/          # start.sh / stop.sh (Docker build + run)
└── .env              # OPENROUTER_API_KEY (never commit)
```

The backend serves the built frontend at `/` via `StaticFiles`. All API routes are under `/api/`.

## Running locally

**First-time setup:**
```bash
uv sync   # creates .venv and installs all deps
```

**Development (hot-reload, two terminals):**
```bash
# Terminal 1 — backend (run from project root)
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```
Frontend proxies API calls to `http://localhost:8000` via `NEXT_PUBLIC_API_BASE_URL`.

**Production (Docker):**
```bash
scripts/start.sh   # builds frontend, copies to backend/static, builds + runs Docker
scripts/stop.sh    # stops and removes container
```
Visit http://localhost:8000

## Auth

Hardcoded demo credentials: **user** / **password**. Sets an httpOnly cookie `pm_mvp_auth=true`. All `/api/board` and `/api/ai/*` routes require this cookie.

## AI

Uses OpenRouter at `https://openrouter.ai/api/v1` with model `openai/gpt-oss-120b`. The `/api/ai/chat` endpoint sends the full board JSON + user question to the model and expects a JSON response `{ reply, board_update }`. If `board_update` is non-null it is validated against the `BoardData` schema and saved.

Set `OPENROUTER_API_KEY` in `.env` at the project root.

## Testing

```bash
# Frontend unit tests (Vitest)
cd frontend && npm test

# Frontend e2e tests (Playwright)
cd frontend && npm run test:e2e

# Backend tests (pytest) — run from project root
uv run python -m pytest backend/tests/
```

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind v4, @dnd-kit |
| Backend | Python 3.14, FastAPI, Pydantic, SQLite |
| AI | OpenRouter (`openai/gpt-oss-120b`) via the `openai` SDK |
| Infra | Docker (single container), uv (Python package manager, local + Docker) |

## Color scheme

- Accent Yellow `#ecad0a` — accent lines, highlights
- Blue Primary `#209dd7` — links, key sections
- Purple Secondary `#753991` — submit buttons, important actions
- Dark Navy `#032147` — main headings
- Gray Text `#888888` — supporting text, labels

## Coding standards

- No over-engineering. No unnecessary defensive programming. No extra features.
- No emojis anywhere.
- Keep READMEs and docs minimal.
- When hitting issues, identify root cause with evidence before fixing.
