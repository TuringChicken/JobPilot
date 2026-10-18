# JobPilot AI

Chrome extension + FastAPI backend that matches a candidate's CV against job postings and produces explainable match reports.

See [JobPilot_AI_Project_Outline.md](JobPilot_AI_Project_Outline.md) for the full design.

## Status

Phase 1 (MVP): single job page + one CV → AI match report. Not started.

## Setup on a new machine

```powershell
git clone https://github.com/<your-username>/JobPilot.git
cd JobPilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# pip install -r requirements.txt   (once the backend exists)
# copy .env.example .env            (then fill in secrets locally)
```

## Daily sync between machines

```powershell
git pull     # before starting
git add .
git commit -m "..."
git push     # before switching machines
```

Never commit `.env`, real resumes, or virtual environments.
