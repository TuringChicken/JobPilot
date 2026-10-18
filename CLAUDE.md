# JobPilot AI — project notes for Claude Code

- Design doc: `JobPilot_AI_Project_Outline.md` (source of truth for scope and architecture).
- Developed on two machines, synced via Git/GitHub. Do not rely on local-only state; record shared conventions here.
- Python work happens in a per-machine `.venv` at the repo root; dependencies go in `requirements.txt` / `pyproject.toml`.
- Secrets live in `.env` (gitignored); keep `.env.example` updated with variable names only.
- Never commit real resumes or personal data; use synthetic sample CVs for tests.
- Current focus: Phase 1 MVP (single job page + CV → match report).
- Python 3.13. Backend lives in `backend/app` (FastAPI app factory `app.main:create_app`); tests in `backend/tests`, run `pytest` from repo root.
- LLM: `LLM_PROVIDER=dashscope` (default, `qwen-plus`, JSON-object mode + schema in prompt + Pydantic validation) or `azure` (v1 API, native json_schema). `app/services/llm.py` `StructuredLLM` handles both; new LLM features should reuse `StructuredLLM.parse`, not create their own clients.
- Tests must never call a real LLM API: conftest builds settings without LLM credentials and injects fakes.
- Matching (`POST /api/jobs/analyze`): LLM extracts the JD (`job_parser.py`, cached per text fingerprint) and judges S/E/R with quotes (`match_evaluator.py`); everything rule-based — hard filters, preference score P, weighted total, quote verification — lives in `services/matching.py` and must stay deterministic. Job page text is untrusted: keep it fenced, never let it reach tools or writes.
- Schema changes go through Alembic migrations (`backend/alembic`), not `create_all`.
