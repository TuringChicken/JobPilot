# JobPilot AI Dev Log

## 2026-10-23: GitHub Actions CI

`.github/workflows/ci.yml` runs two jobs on pushes to `main`, on PRs and on manual dispatch.

| Job | Steps |
|---|---|
| backend | Python 3.13, `pip install -r requirements-dev.txt`, `ruff check`, `ruff format --check`, `pytest` (`live` tests excluded by the pyproject default) |
| extension | Node 24, `npm ci`, `npm test` (vitest, including the i18n key-consistency check), `npm run build` (including `tsc --noEmit`) |

CI configures no LLM credentials and no `.env`: the tests use fakes and a temporary SQLite database, so no secrets are needed.

Also added `.github/workflows/live.yml`: manual dispatch only, choice of dashscope / azure, reads secrets from the `live-llm` Environment and runs `pytest -m live -s`. When credentials are missing it fails instead of skipping everything. Setup is described in section 11 of `BACKEND.md`.

## 2026-10-21: "Analyze again" for past reports

### Background

After editing the resume based on a first analysis, seeing how the new resume matched meant going back to the job page, reading it again and re-analysing. And because the extension sends the whole page's text, any change in the page's dynamic content made the JD parsing cache (keyed on a fingerprint of the full text) miss, which meant two LLM calls again.

### Results

| Item | Details |
|---|---|
| `POST /api/matches/{id}/reanalyze` | Re-evaluates using the saved job text and parsed JD plus the current profile/preferences, with a single LLM call; creates a new report and keeps the old one |
| Refactoring | Loading the profile/preferences and evaluating + saving a report moved into `matches.py` (`load_candidate`, `evaluate_and_store`), shared by `/api/jobs/analyze` and re-analysis |
| Extension | Opening a report from History shows an "Analyze again" button; the new report is shown when it finishes; the History tab shows a spinner while it runs; switching to another report means the result won't overwrite the current view |
| Tests | 3 new backend tests: only the evaluator is called, the re-uploaded profile is used, the old report is kept, the truncation flag carries over, 404/422/502 |

### Notes

- Uploading a new resume only replaces the profile and doesn't delete past reports (only deleting the profile clears them), so after editing the resume you can re-analyse straight from History.
- Tried a "same URL + text similarity" fallback to raise the JD cache hit rate; it didn't fit the actual need and was dropped.

### Weight change

The overall-score weights changed from `0.35S + 0.25E + 0.20R + 0.20P` to `0.35S + 0.25E + 0.30R + 0.10P`: more weight on responsibilities, less on preferences. Still not calibrated with labelled data. Saved reports keep the weights and total they were created with and are not recalculated; use "Analyze again" in History for a new score.

## 2026-10-20: Visa / work rights in the resume profile

- **Problem**: the parsed resume had no visa status. `CandidateProfileData` had no field for it and the prompt didn't ask for it, while the JD side already had `work_rights`.
- **Fix**: added `work_rights: str | None` to the profile, with the same name as the JD field. The prompt says to copy it verbatim (including expiry dates) only when the resume explicitly states a visa, residency, citizenship or work permit, never to infer it from nationality, location, education or languages, and to leave it null otherwise.
- **Evaluation**: the `match_evaluator` prompt asks the model to compare the profile's and the JD's `work_rights` and add an uncertainty when either is missing or they may not match. It must not judge "eligible / not eligible" (in line with the outline's rule against definitive judgements about visa eligibility). The hard filter is unchanged and stays deterministic.
- **Extension**: the Resume page shows "Visa / work rights" under the summary; when the resume doesn't state it, a hint says `work_rights` can be added under "Edit". `types.ts` updated to match the backend.
- **Migration** `37bb9f4319e7`: backfills `work_rights: null` on existing profiles and supports downgrade; tested upgrade → downgrade → upgrade on a copy of the database. **After pulling on the other machine, run `.venv/bin/alembic upgrade head`.**
- **Logging**: while debugging a resume-parsing `ValidationError`, the log only had the exception type, which wasn't enough to find the cause. `llm.py` now also logs the failing field path and error type (e.g. `skills.3.proficiency (literal_error)`) but not field values, so resume content stays out of the logs; a test enforces this.
- **Tests**: added `test_parser_keeps_work_rights` and added `work_rights` to the prompt field check; the smoke test's synthetic CV gained a work-rights line with an assertion that it gets extracted (not yet run against the real model). 107 backend tests and 13 extension tests pass, `ruff` passes.

## 2026-10-19 – 2026-10-20: Unified model, smoke tests, Chrome extension

### Results

Finished the extension side of Phase 1: **open a job page → click the extension → see an evidence-backed match report in the side panel**. The Phase 1 loop is complete.

| Item | Status | Details |
|---|---|---|
| Unified default model | ✅ | Everything now uses `qwen3.8-27b` (`config.py`, `.env.example`, `README.md`, tests) |
| Real-model smoke tests | ✅ | `backend/tests/test_live.py`, skipped by default, run manually with `pytest -m live -s` |
| Known-issues list | ✅ | `docs/KNOWN_ISSUES.md`, 16 items, graded P1–P3 |
| Chrome extension | ✅ | Five parts: Analyze, Report, Resume, History, Settings |
| Language option | ✅ | Simplified Chinese / English, controls both UI and report text |
| Save, delete, export to Markdown | ✅ | Backend gained a `saved` field and endpoints |

### Chrome extension

Lives in `extension/`: a Manifest V3 side-panel extension built with React + TypeScript + Vite. After `npm run build`, load `extension/dist` in `chrome://extensions`.

| Page | Features |
|---|---|
| Analyze | Reads the visible text of the current tab and analyses it; if you first select a job description of 200+ characters, only the selection is analysed |
| Report | Overall score, hard requirements, S/E/R/P (expand for reasoning and verbatim quotes; unverified ones marked ⚠), matched skills, skill gaps, uncertainties; save / export to Markdown / delete |
| Resume | Upload PDF/DOCX, view the parsed result, edit as JSON, confirm |
| History | Toggle all / saved, open a full report |
| Settings | Language, backend URL, API key (stored in `chrome.storage.local`, not synced) |

### Key technical decisions

| Decision | Reason |
|---|---|
| Side panel instead of popup | Analysis takes about 30 seconds; a popup closes as soon as it loses focus and the request is cut off |
| Read the page on click with `chrome.scripting` + `activeTab` | Minimal permissions, no persistent content script; if the page can't be read, the user can grant the optional "read site content" permission |
| Extension calls the backend directly, no CORS changes | Extension pages aren't subject to CORS for hosts they have permission for |
| Keep every page mounted | Switching tabs doesn't lose an analysis or upload in progress; the tab bar shows a spinner |
| Errors thrown as codes and translated by the UI | Error messages change with the language too |
| Language code also sent to the backend | Model-written explanations follow the user's language; quotes, skill names and condition text stay verbatim, so verification isn't affected |
| Every analysis saved automatically; saving only marks it | Results can still be found in History after closing the side panel |
| Export uses the system "Save as" dialog | The user picks where to save; falls back to a normal download when unavailable, no `downloads` permission needed |

### Backend changes

- `POST /api/jobs/analyze` gained an optional `language` parameter (BCP 47, default `en`; a malformed value returns 422).
- `match_results` gained a `saved` field (migration `a138acf143ff`, tested upgrade → downgrade → upgrade on a copy of the database).
- Added `PATCH /api/matches/{id}` (save), `DELETE /api/matches/{id}` and `GET /api/matches?saved=`.
- **After pulling on the other machine, run `.venv/bin/alembic upgrade head`.**

### Smoke test results (`qwen3.8-27b`)

| Test | Run 1 | Run 2 |
|---|---|---|
| Resume parsing | 9.0s, pass | 10.5s, pass |
| Normal job | 68, 30.8s | 60, 31.3s |
| With "give full marks" injection | 60, 26.5s | 69, 28.0s |
| Chinese report | — | 61, 31.8s; reasoning in Chinese, quotes still verify |
| Not a job page | 422, 2.7s | 422, 3.8s |

Resume-parsing checks: no name or contact details leaked, internship went into work experience, the injected fake skill wasn't recorded, languages and awards were recorded.

Findings:
- `27b` analysis time (26–32 seconds) is close to the earlier `max`; the bottleneck is match evaluation. Try `flash` for speed.
- The overall score for the same job varied between 60 and 69, with single dimensions differing by up to 15 points, more than the earlier ±10 estimate.
- In run 2 the injected version scored 9 points higher than the normal one. It wasn't pushed to full marks, but a single comparison can't tell whether the injection has a slight effect; this needs repeated sampling to compare distributions (recorded as KNOWN_ISSUES #2).

### Tests and verification

- 106 backend tests pass (plus 5 smoke tests skipped by default); `ruff check` and `ruff format --check` pass.
- 13 extension vitest unit tests pass (error messages, formatting, language detection and matching keys across locales, settings validation, Markdown export); `tsc` type checking and the build pass.
- Tested by hand in real Chrome.

### Other notes

- `docs/` was briefly kept local-only; it's committed to GitHub again, and the two machines sync docs through Git.
- Added KNOWN_ISSUES #16: closing the side panel loses the display of a task in progress (the backend still finishes and saves it).

### Next steps

1. Edit job preferences in the extension (currently still done through `/docs`).
2. Tackle the KNOWN_ISSUES P1 items: location matching (#1), evaluation set and weight calibration, repeated-sampling evaluation of injection impact (#2).
3. Use the smoke tests to compare quality and latency of `qwen3.8-flash`.
4. Optional: auto-clean unsaved records; "was this accurate?" feedback; resume tasks after closing the side panel (#16).

---

## 2026-10-19: Second machine setup, resume-parsing fixes, backend docs

### Results

| Item | Status | Details |
|---|---|---|
| Second machine setup | ✅ | Installed dependencies, created `.env` (separate `API_KEY`), `alembic upgrade head`, health check passes |
| End-to-end parsing of a real CV | ✅ | Found 3 problems (below) |
| Resume-parsing fixes | ✅ | Internship classification, name redaction, new languages and awards fields |
| Backend internals doc | ✅ | `docs/BACKEND.md`, with Mermaid flowcharts, a sequence diagram and an ER diagram |

### Problems found with a real CV, and fixes

Parsed my own real CV (used only on this machine, never in Git) with `qwen3.8-27b` and compared it with the PDF:

| Problem | Impact | Fix |
|---|---|---|
| Internships with a title and dates were put in `projects` | Title and dates lost; experience score E too low | Prompt rule: internships with a title and dates go into `work_experience` |
| The candidate's name appeared in project descriptions | Breaks the "no name in structured data" rule, and gets sent to the evaluator | Prompt says the name may only go into `candidate_name`; the code's `redact_name` then replaces the name in every field with "the candidate" and drops that field |
| Languages and awards not recorded | The profile had no fields for them; language requirements are common in job ads | Added `languages` and `awards` to `CandidateProfileData` |

Name-redaction rules: the full name matches case-insensitively and in either order; individual name parts match case-sensitively (so "Will" doesn't hit "will"), and parts shorter than 3 letters are not replaced on their own (so "Ma" and "Li" don't cause false hits).

Re-parsing the same CV after the fixes: internships are in work experience with their dates; the name no longer appears in the structured data; languages and awards are recorded; all other fields match the pre-fix result.

### Data migration

- New migration `14eb892a0f74`: adds empty `languages` and `awards` to existing profiles' JSON, supports downgrade. Tested upgrade → downgrade → upgrade on the local database without problems.
- **After pulling the code on the other machine, run `.venv/bin/alembic upgrade head`.** Otherwise old profiles lack the new fields and fail validation when read.

### Tests

- Added `backend/tests/test_resume_parser.py` with 8 tests. Only the OpenAI client's `create` is replaced with a fake; prompt assembly, JSON validation, dropping `candidate_name` and name redaction all run the real code.
- All test data uses fictional names (Jane Doe, Xiaoming Li, Will Smith).
- 100 tests pass; `ruff check` and `ruff format --check` pass.

### Other notes

- Default model changed to `qwen3.8-27b` (`.env` and `CLAUDE.md`). Note: the defaults in `config.py` and `.env.example` are still `qwen-plus`.
- Resume parsing takes about 44–47 seconds (the real CV is long), much slower than the 9 seconds in the earlier comparison (which used a shorter synthetic resume).
- Existing behaviour confirmed while writing the docs: jobs can be analysed with an unconfirmed profile (the report shows `profile_confirmed: false`); the JD cache is global; match evaluation calls the LLM every time and isn't cached.

### Next steps

1. Chrome extension (Node.js v24 is ready on this machine).
2. Unify the default model configuration (`config.py` / `.env.example`).
3. Consider optional real-model smoke tests (e.g. `pytest -m live`, skipped by default).
4. Carried over from last time: model comparison, evaluation set, formula syntax in the outline, LICENSE.

---

## 2026-10-18 – 2026-10-19: Phase 1 backend MVP

### Results

Finished the Phase 1 backend loop: **upload resume → set job preferences → analyse a job → produce an evidence-backed match report**. The Chrome extension hasn't been started.

| Module | Status | Details |
|---|---|---|
| Project setup | ✅ | Git repo, `.gitignore`, `README.md`, `CLAUDE.md`, Python 3.13 virtual environment |
| Backend skeleton | ✅ | FastAPI app factory, config loading, SQLAlchemy + Alembic, API key auth |
| Resume upload and parsing | ✅ | PDF/DOCX text extraction → LLM structuring → user review and confirmation |
| Job preferences | ✅ | Location, work arrangement, employment type, seniority, salary, must-haves, deal-breakers |
| Job analysis and matching | ✅ | JD structuring, hard-requirement filtering, three-dimension LLM scoring, evidence verification, weighted total |
| LLM integration | ✅ | DashScope (default) / Azure OpenAI, switchable in config |
| Chrome extension | ⏳ | Next |

### API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check (no auth) |
| POST | `/api/profile/resume` | Upload and parse a resume |
| GET / PATCH / DELETE | `/api/profile` | View / edit and confirm / delete the profile (also deletes match reports) |
| GET / PATCH / DELETE | `/api/preferences` | View / partially update / reset job preferences |
| POST | `/api/jobs/analyze` | Analyse the current job and produce a match report |
| GET | `/api/matches`, `/api/matches/{id}` | List past reports / report detail |

Every endpoint except `/api/health` requires the `X-API-Key` header. Interactive docs: start the server and open `http://127.0.0.1:8000/docs`.

### Matching flow

1. **Clean the job text**: strip prompt delimiter tags (to prevent spoofing), normalise whitespace, cap at 20,000 characters.
2. **Structure the JD (LLM)**: cached by text fingerprint so the same job isn't parsed twice; non-job pages return 422.
3. **Match evaluation (LLM)**: scores skills S, experience E and responsibilities R (0–100), with verbatim CV/JD quotes, skill gaps and uncertainties. Only the structured profile is sent, not the raw resume with contact details.
4. **Rule-based calculation (code, deterministic)**:
   - Hard-requirement filter: missing information is "needs review", not a mismatch.
   - Preference score P: average of pass 100 / needs review 50 / mismatch 0.
   - Total: `0.35S + 0.25E + 0.20R + 0.20P` (initial weights, to be calibrated).
   - Evidence verification: each quote is checked against the profile or the JD; quotes that can't be found are marked `verified: false`.

### Key technical decisions

| Decision | Reason |
|---|---|
| SQLite for now | A single-user MVP doesn't need a database server; access goes through SQLAlchemy, so moving to PostgreSQL + pgvector in Phase 2 only needs a new connection string and a migration |
| `pypdf` for PDF parsing instead of PyMuPDF | PyMuPDF is AGPL, which conflicts with the MIT licence common for public repos |
| No contact details extracted | Data minimisation; name, email and phone never enter the structured data |
| Re-uploading a resume resets "confirmed" | A new parse must be reviewed by the user |
| Preferences and resume in separate tables | Preferences are wishes, the resume is facts; keeps the model from mixing them up |
| Scores weighted in code, not a total from the LLM | Explainable, reproducible, testable |
| LLM calls wrapped in `StructuredLLM` | Shared by resume parsing, JD parsing and match evaluation; switching providers is only a config change |
| DashScope uses JSON mode + Pydantic validation | Not confirmed whether it supports strict json_schema; validation failures return 502 and bad data is never stored |
| LLM environment variables isolated in tests | Prevents an API key on the dev machine from making tests call the real API |

### How the LLM provider changed

1. **Azure OpenAI**: the original plan; paused when the free credit ran out.
2. **Local Ollama (qwen3:8b)**: worked, but with thinking off it followed injected instructions in the resume; with thinking on a single call took about 77 seconds. Removed.
3. **DashScope (current default)**: OpenAI-compatible API, good on both speed and injection resistance. The Azure path is kept; set `LLM_PROVIDER=azure` to switch back.

Resume-parsing model comparison (same synthetic resume × 3 runs, including an injection test):

| Model | Avg. time | Errors | Injected | Quality issues |
|---|---|---|---|---|
| qwen3.8-27b | 9.0s | 0/3 | 0/3 | None |
| qwen3.8-flash | 5.7s | 0/3 | 0/3 | None |
| qwen-plus | 9.5s | 0/3 | 0/3 | None |

The sample is tiny; it only shows that all of them work, not which is better. The current `.env` uses `qwen3.8-max` (not in the comparison above).

### Tests and verification

- **Automated tests**: 92, all passing. They cover text extraction, auth, upload, preference validation, every branch of the hard filter, hourly/annual salary conversion, evidence verification, the weighted calculation, injection-tag stripping, caching, error handling and cascading deletes. All tests use fake LLMs and never call external APIs.
- **Linting**: `ruff check` and `ruff format --check` pass.
- **End-to-end run** (DashScope `qwen3.8-max`, temporary database, synthetic resume and job):

| | Normal job | With "give full marks" injection |
|---|---|---|
| Total | 67 | 68 |
| S / E / R / P | 65 / 40 / 70 / 100 | 75 / 40 / 60 / 100 |
| Time | 26.5s | 34.0s |

The injection didn't work (no full marks, and Kubernetes was still listed as a missing skill). The report correctly pointed out missing Azure, under 1 year of experience and unstated visa status.

### Problems found and fixed

- SQLite doesn't store time zones, so timestamps lost their UTC marker when read back → added a `UTCDateTime` column type and a regression test.
- Empty settings in `.env` made startup fail → empty values now fall back to defaults.
- The local model turned "Dec 2024" into `2024-12-01` → the prompt now says to copy dates verbatim.
- Pydantic ran the regex check before upper-casing, so lower-case currency codes were rejected → the regex now accepts both cases.

### Known limitations

- **Single dimension scores vary by about ±10 points** (the total is more stable); needs a hand-labelled evaluation set to calibrate.
- **Some judgements are lenient**, e.g. counting a semantic-search project as RAG experience; the report includes the evidence so a human can judge.
- **Analysis takes 26–34 seconds** (two LLM calls, `qwen3.8-max`); `qwen3.8-flash` is worth evaluating.
- **Location matching is a simple substring check**: a job saying "New Zealand" with a preference of "Auckland" counts as a mismatch.
- **Scanned PDFs aren't supported** (no OCR).
- **Auth is a single API key**, only suitable for one user.
- **The database isn't synced through Git**; the two machines are independent (on purpose, to keep personal data out of the public repo).
- Resume and job content is sent to Alibaba Cloud DashScope for processing.

### Next steps

1. **Chrome extension** (Manifest V3 + React + TypeScript + Vite): read the current page, call `/api/jobs/analyze`, show the report. Install Node.js LTS first.
2. Compare match-evaluation quality and latency across `qwen3.8-flash` / `27b` / `max`.
3. Build a hand-labelled CV–JD evaluation set to calibrate the weights and measure variance.
4. To do: fix the formula syntax in the outline (`\[ \]` → `$$`); add a LICENSE.
