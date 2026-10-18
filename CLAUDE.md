# JobPilot AI — project notes for Claude Code

- Design doc: `JobPilot_AI_Project_Outline.md` (source of truth for scope and architecture).
- Developed on two machines, synced via Git/GitHub. Do not rely on local-only state; record shared conventions here.
- Python work happens in a per-machine `.venv` at the repo root; dependencies go in `requirements.txt` / `pyproject.toml`.
- Secrets live in `.env` (gitignored); keep `.env.example` updated with variable names only.
- Never commit real resumes or personal data; use synthetic sample CVs for tests.
- Current focus: Phase 1 MVP (single job page + CV → match report).
- Python 3.13. Backend lives in `backend/app` (FastAPI app factory `app.main:create_app`); tests in `backend/tests`, run `pytest` from repo root.
- LLM: Azure OpenAI only (v1 API). `app/services/llm.py` `StructuredLLM` wraps it via `chat.completions.parse`; new LLM features should reuse `StructuredLLM.parse`, not create their own clients.
- Tests must never call the real Azure OpenAI API: conftest builds settings without Azure credentials and injects fakes.
- Schema changes go through Alembic migrations (`backend/alembic`), not `create_all`.
