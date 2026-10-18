# JobPilot AI

Chrome extension + FastAPI backend that matches a candidate's CV against job postings and produces explainable match reports.

See [JobPilot_AI_Project_Outline.md](JobPilot_AI_Project_Outline.md) for the full design.

## Status

Phase 1 (MVP): single job page + one CV → AI match report. Backend skeleton with resume upload/parsing is in place.

## Setup on a new machine

```powershell
git clone https://github.com/TuringChicken/JobPilot.git
cd JobPilot
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env      # then set API_KEY and Azure OpenAI values
alembic upgrade head        # creates data/jobpilot.db
```

## LLM provider

Default is local [Ollama](https://ollama.com) (`LLM_PROVIDER=ollama`, model `qwen3:8b`):

```powershell
ollama pull qwen3:8b
```

Ollama's default 4096-token context is too small for resume + reasoning. Raise it (then restart Ollama):

```powershell
setx OLLAMA_CONTEXT_LENGTH 8192
```

To use Azure OpenAI instead, set `LLM_PROVIDER=azure` and the `AZURE_OPENAI_*` values in `.env`.

## Run the backend

```powershell
uvicorn app.main:create_app --factory --app-dir backend --reload
```

API docs: http://127.0.0.1:8000/docs. All `/api/profile*` endpoints need the `X-API-Key` header.

## Test and lint

```powershell
pytest
ruff check . ; ruff format --check .
```

After changing `backend/app/models.py`: `alembic revision --autogenerate -m "..."` then `alembic upgrade head`.

## Daily sync between machines

```powershell
git pull     # before starting
git add .
git commit -m "..."
git push     # before switching machines
```

Never commit `.env`, real resumes, or virtual environments.
