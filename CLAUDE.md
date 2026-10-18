# JobPilot AI — project notes for Claude Code

- Design doc: `JobPilot_AI_Project_Outline.md` (source of truth for scope and architecture).
- Developed on two machines, synced via Git/GitHub. Do not rely on local-only state; record shared conventions here.
- Python work happens in a per-machine `.venv` at the repo root; dependencies go in `requirements.txt` / `pyproject.toml`.
- Secrets live in `.env` (gitignored); keep `.env.example` updated with variable names only.
- Never commit real resumes or personal data; use synthetic sample CVs for tests.
- Current focus: Phase 1 MVP (single job page + CV → match report).
