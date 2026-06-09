# High level steps for project

Part 1: Plan

Enrich this document to plan out each of these parts in detail, with substeps listed out as a checklist to be checked off by the agent, and with tests and success critieria for each. Also create an AGENTS.md file inside the frontend directory that describes the existing code there. Ensure the user checks and approves the plan.

Decisions (recorded):

- **OpenRouter model:** `openai/gpt-oss-120b` via OpenRouter (use this model for AI calls).
- **Python package manager in Docker:** `uv` (use `uv` as specified, not `pip`).
- **SQLite database filename:** `kanban.db` (file-based DB at project root or `backend/data/kanban.db`).
- **OpenRouter API key:** `OPENROUTER_API_KEY` is set in the repository `.env` (no further action needed to obtain the key).
- **Backend test framework:** `pytest` (use `pytest` for backend unit and integration tests).
- **Docker layout:** single Docker container running the FastAPI backend which will serve the statically built Next.js frontend at `/` (FastAPI serves the built files).

Enrichment notes:

- This `docs/PLAN.md` will be updated incrementally as implementation decisions are made and as features are completed. Each Part below should include explicit success criteria and tests before work begins.
- The frontend already contains a demo Kanban; the plan assumes we will statically build it (`next build` + `next export` or `next build` and copy `.next` static files) and serve via FastAPI.
- Database path recommendation: create a `backend/data/` directory and place `kanban.db` there; the backend should create the DB file if it doesn't exist.
- CI / local run recommendation: provide simple `scripts/start.sh` and `scripts/stop.sh` (or platform-specific variants) that build the frontend, start the backend in Docker, and run tests.

Action: the agent will update this file with more detailed substeps and test criteria as each Part is started.

Part 2: Scaffolding

Set up the Docker infrastructure, the backend in backend/ with FastAPI, and write the start and stop scripts in the scripts/ directory. This should serve example static HTML to confirm that a 'hello world' example works running locally and also make an API call.

Part 3: Add in Frontend

Now update so that the frontend is statically built and served, so that the app has the demo Kanban board displayed at /. Comprehensive unit and integration tests.

Part 4: Add in a fake user sign in experience

Now update so that on first hitting /, you need to log in with dummy credentials ("user", "password") in order to see the Kanban, and you can log out. Comprehensive tests.

Part 5: Database modeling

Now propose a database schema for the Kanban, saving it as JSON. Document the database approach in docs/ and get user sign off.

Part 6: Backend

Now add API routes to allow the backend to read and change the Kanban for a given user; test this thoroughly with backend unit tests. The database should be created if it doesn't exist.

Part 7: Frontend + Backend

Now have the frontend actually use the backend API, so that the app is a proper persistent Kanban board. Test very throughly.

Part 8: AI connectivity

Now allow the backend to make an AI call via OpenRouter. Test connectivity with a simple "2+2" test and ensure the AI call is working.

Part 9: Now extend the backend call so that it always calls the AI with the JSON of the Kanban board, plus the user's question (and conversation history). The AI should respond with Structured Outputs that includes the response to the user and optionaly an update to the Kanban. Test thoroughly.

Part 10: Now add a beautiful sidebar widget to the UI supporting full AI chat, and allowing the LLM (as it determines) to update the Kanban based on its Structured Outputs. If the AI updates the Kanban, then the UI should refresh automatically.