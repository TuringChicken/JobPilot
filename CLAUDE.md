# JobPilot AI — project notes for Claude Code

- Design doc: `JobPilot_AI_Project_Outline.md` (source of truth for scope and architecture).
- Developed on two machines, synced via Git/GitHub. Do not rely on local-only state; record shared conventions here.
- Python work happens in a per-machine `.venv` at the repo root; dependencies go in `requirements.txt` / `pyproject.toml`.
- Secrets live in `.env` (gitignored); keep `.env.example` updated with variable names only.
- Never commit real resumes or personal data; use synthetic sample CVs for tests.
- Current focus: Phase 1 MVP (single job page + CV → match report).
- Python 3.13. Backend lives in `backend/app` (FastAPI app factory `app.main:create_app`); tests in `backend/tests`, run `pytest` from repo root.
- LLM: `app/services/llm.py` `StructuredLLM` wraps any OpenAI-compatible endpoint via `chat.completions.parse`. `LLM_PROVIDER=ollama` (default, local `qwen3:8b`) or `azure`. New LLM features should reuse `StructuredLLM.parse`, not create their own clients.
- Tests must never call a real LLM (Ollama or Azure): conftest uses `llm_provider="azure"` without credentials and injects fakes.
- Schema changes go through Alembic migrations (`backend/alembic`), not `create_all`.
