# JobPilot AI

Chrome extension + FastAPI backend that matches a candidate's CV against job postings and produces explainable match reports.

See [JobPilot_AI_Project_Outline.md](JobPilot_AI_Project_Outline.md) for the full design.

## Status

Phase 1 (MVP): single job page + one CV → AI match report. Backend (resume parsing, preferences, job analysis, match reports) is done; the Chrome extension can analyze the current page and show reports. Resume upload and preferences are still edited through the API docs page.

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

## LLM

Select with `LLM_PROVIDER` in `.env`. Without credentials for the selected provider, resume upload returns 503.

- `dashscope` (default): Alibaba Cloud Model Studio, OpenAI-compatible mode. Set `DASHSCOPE_API_KEY`; use the `dashscope-intl` base URL if your key is from the international site. Default model `qwen3.8-27b`.
- `azure`: Azure OpenAI v1 API. Set `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_CHAT_DEPLOYMENT` (the deployment name, not the model name).

## Run the backend

```powershell
uvicorn app.main:create_app --factory --app-dir backend --reload
```

API docs: http://127.0.0.1:8000/docs. All `/api/profile*` endpoints need the `X-API-Key` header.

## Chrome extension

Side panel extension in `extension/` (Manifest V3, React, TypeScript, Vite). Needs Node.js 20+.

```powershell
cd extension
npm install
npm run build        # outputs extension/dist; `npm run dev` rebuilds on change
```

Load it: `chrome://extensions` → enable Developer mode → "Load unpacked" → select `extension/dist`. After a rebuild, click the reload icon on the extension card.

Use it: start the backend, click the JobPilot toolbar icon to open the side panel, enter the backend URL and the `API_KEY` from `.env` under 设置, then open a job posting and click 分析当前页面. The page is read only when you click; select the job description first (200+ characters) to analyze just that part.

## Test and lint

```powershell
pytest
ruff check . ; ruff format --check .
pytest -m live -s                     # optional: smoke tests against the real LLM in .env
cd extension; npm run build; npm test  # extension typecheck, build, unit tests
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
