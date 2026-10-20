# JobPilot AI — project notes for Claude Code

- Design doc: `JobPilot_AI_Project_Outline.md` (source of truth for scope and architecture).
- Developed on two machines, synced via Git/GitHub. Do not rely on local-only state; record shared conventions here.
- Python work happens in a per-machine `.venv` at the repo root; dependencies go in `requirements.txt` / `pyproject.toml`.
- Secrets live in `.env` (gitignored); keep `.env.example` updated with variable names only.
- `docs/`: `DEVLOG.md` (dev log, newest first), `KNOWN_ISSUES.md` (known issues and limits, P1–P3), `BACKEND.md` (backend internals). Committed; keep them updated with the code.
- Never commit real resumes or personal data; use synthetic sample CVs for tests.
- Current focus: Phase 1 MVP (single job page + CV → match report).
- Python 3.13. Backend lives in `backend/app` (FastAPI app factory `app.main:create_app`); tests in `backend/tests`, run `pytest` from repo root.
- LLM: `LLM_PROVIDER=dashscope` (default, `qwen3.8-27b`, JSON-object mode + schema in prompt + Pydantic validation) or `azure` (v1 API, native json_schema). `app/services/llm.py` `StructuredLLM` handles both; new LLM features should reuse `StructuredLLM.parse`, not create their own clients.
- Tests must never call a real LLM API: conftest builds settings without LLM credentials and injects fakes.
- Live smoke tests (`backend/tests/test_live.py`) are the only exception to the no-real-LLM rule: marked `live`, skipped by default, run manually with `.venv/bin/pytest -m live -s` after prompt/model changes.
- Matching (`POST /api/jobs/analyze`): LLM extracts the JD (`job_parser.py`, cached per text fingerprint) and judges S/E/R with quotes (`match_evaluator.py`); everything rule-based — hard filters, preference score P, weighted total, quote verification — lives in `services/matching.py` and must stay deterministic. Job page text is untrusted: keep it fenced, never let it reach tools or writes.
- Chrome extension lives in `extension/` (MV3 side panel, React + TS + Vite; `npm run build` → load `extension/dist` unpacked). Page text is read only on the user's click via `chrome.scripting` + `activeTab`; no persistent content scripts or broad host permissions by default. `src/lib/types.ts` mirrors the backend schemas — update both together. API key lives in `chrome.storage.local`. UI strings live in `extension/src/i18n` (`zh-CN.ts` defines the keys; every locale must match, a test checks); the chosen locale is also sent as `language` to `/api/jobs/analyze` so model-written report text follows it, while quotes stay verbatim.
- Schema changes go through Alembic migrations (`backend/alembic`), not `create_all`.
