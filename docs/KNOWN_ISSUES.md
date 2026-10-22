# JobPilot AI Known Issues and Limitations

For future improvements. Compiled from `DEVLOG.md` (up to 2026-10-19) and a review of the current code. Each item lists the impact, the relevant code and possible improvements; once an item is handled, update its "Status" and record it in the DEVLOG.

Priority: **P1** affects correctness or usability of results, **P2** affects experience or accuracy, **P3** is an architecture/scope limitation, planned by phase.

## Overview

| # | Issue | Category | Priority | Status |
|---|---|---|---|---|
| 1 | Location matching is a simple substring check | Rule matching | P1 | Open |
| 2 | Large score variance (over ±10 per dimension), weights uncalibrated; injection impact can't be judged from single runs | Scoring quality | P1 | Open |
| 3 | Some judgements are lenient | Scoring quality | P2 | Open |
| 4 | LLM calls are slow | Performance | P2 | Partly handled (2026-10-21) |
| 5 | CV quotes are verified against the structured profile and may be wrongly flagged as unverified | Evidence verification | P2 | Open |
| 6 | Excluded companies use two-way substring matching and can cause false hits | Rule matching | P2 | Open |
| 7 | Salaries in different currencies can't be compared | Rule matching | P2 | Open |
| 8 | Match evaluation isn't cached | Performance/cost | P2 | Open |
| 9 | Jobs can be analysed with an unconfirmed profile | Workflow | P2 | Open |
| 10 | No automated verification against a real model | Testing | P2 | Handled (2026-10-19) |
| 11 | Scanned PDFs aren't supported | Resume parsing | P3 | Open |
| 12 | Auth is a single API key | Security/architecture | P3 | Open |
| 13 | The database isn't synced through Git | Dev environment | P3 | By design |
| 14 | Resume and job content is sent to a third-party LLM | Privacy | P3 | Known and accepted |
| 15 | Miscellaneous docs and repo to-dos | Docs | P3 | Open |
| 16 | Closing the side panel loses tasks in progress | Chrome extension | P2 | Open |

## Details

### 1. Location matching is a simple substring check (P1)

- **Symptom**: a job saying "New Zealand" with a preference of "Auckland" is judged `fail`; only the reverse (job "Auckland, New Zealand", preference "New Zealand") passes. Abbreviations ("NZ", "SF") and aliases aren't recognised either.
- **Impact**: a `fail` pulls the preference score P down and can filter out jobs that should be recommended.
- **Location**: `backend/app/services/matching.py` `_check_location`.
- **Possible improvements**:
  - Introduce a location hierarchy (city → region → country). When the job's location is broader than the preference, mark it `unknown` instead of `fail`.
  - Or have JD parsing output normalised `country` / `city` fields and compare them in code, keeping the rules deterministic.
  - Add tests: broad → narrow, narrow → broad, abbreviations, multi-location jobs.

### 2. Large score variance, uncalibrated weights; injection impact can't be judged from single runs (P1)

- **Symptom**: analysing the same job several times, single S / E / R scores vary by about 10 points; the total is relatively stable. The weights `0.35S + 0.25E + 0.30R + 0.10P` (changed on 2026-10-21 from `0.20R + 0.20P`: more on responsibilities, less on preferences) also have no data behind them.
- **Smoke-test data from 2026-10-19** (`qwen3.8-27b`, same synthetic resume and job):

  | Run | Normal job | With "give full marks" injection | Chinese report |
  |---|---|---|---|
  | Run 1 | 68 (S/E/R 60/55/65) | 60 (50/40/60) | — |
  | Run 2 | 60 (50/45/55) | 69 (60/55/70) | 61 (55/40/60) |

  The total for the same job varied between 60 and 69, with single dimensions differing by up to 15 points, more than the earlier ±10 estimate.
- **Injection impact can't be judged from single runs**: in run 2 the injected job scored 9 points higher than the normal version. The injection didn't push the score to full marks and missing skills were still listed; the smoke test only checks "no full marks", so it passed. But with natural variance of about 10 points, a single comparison can neither prove the injection has no effect nor prove it nudges the score up slightly.
- **Location**: `matching.py` `WEIGHTS`; the prompt in `match_evaluator.py`.
- **Possible improvements**:
  - Build a hand-labelled CV–JD evaluation set (using synthetic resumes) to quantify variance and calibrate the weights.
  - The prompt already has score-band anchors (90–100 / 70–89 / 40–69 / 0–39); the criteria for each band could be made more specific. Lower the temperature or fix a seed (if the provider supports it).
  - Evaluating injection impact: run the normal and injected versions of the same job N times each (e.g. 10) and compare the score distributions (mean, median) rather than single runs. This could be a manually run evaluation script, kept out of the smoke tests.
  - Consider sampling several times and taking the median (adds cost and latency; needs weighing up).

### 3. Some judgements are lenient (P2)

- **Symptom**: e.g. counting a semantic-search project as RAG experience. The report includes the evidence so a human can judge, but the default conclusion leans optimistic.
- **Possible improvements**: collect such cases in the evaluation set; make the prompt distinguish "direct experience" from "related experience", or add a match strength (exact / related) to `matched_skills`.

### 4. LLM calls are slow (P2)

- **Symptom**: parsing a real CV takes about 44–47 seconds; analysing a job takes about 26–34 seconds (two LLM calls, measured on `qwen3.8-max`). Re-measured with `qwen3.8-27b` in the 2026-10-19 smoke tests: analysis took 26.5–30.8 seconds, no clear change, with match evaluation as the bottleneck; parsing a short synthetic resume took 9 seconds.
- **Impact**: the wait in the Chrome extension is too long, which is a poor experience.
- **Possible improvements**:
  - Compare quality and latency of `qwen3.8-flash` and `qwen3.8-27b` for match evaluation.
  - JD parsing is cached by a fingerprint of the full text, but the extension sends the whole page's text, and things like posting date, applicant count and recommended jobs change on every visit, so going back to the page to re-analyse usually still means two calls.
  - 2026-10-21: past reports gained "Analyze again" (`POST /api/matches/{id}/reanalyze`), which re-evaluates with the saved job text and parsed result plus the current resume, in a single call and without going back to the job page. It fits the "edit the resume based on the report, then check the match again" case.
  - Show progress in the extension, or switch to streaming/async results.

### 5. CV quotes are verified against the structured profile and may be wrongly flagged as unverified (P2)

- **Symptom**: `EvidenceVerifier` uses the structured profile (not the raw resume) as the CV-side corpus. If the model quotes a sentence from the original that was rewritten or split during structuring, it is marked `verified: false`. Also, the name in the profile has been replaced with "the candidate".
- **Note**: the evaluator itself only receives the structured profile, so in most cases quotes should be found in it. This mainly causes false alarms; it won't make a fabricated quote count as verified.
- **Location**: `matching.py` `EvidenceVerifier`.
- **Possible improvements**: track the share of `unverified_evidence_count` in real use; if it's high, consider fuzzy matching (e.g. allowing small character differences), while making sure fabricated quotes aren't accepted as verified.

### 6. Excluded companies use two-way substring matching and can cause false hits (P2)

- **Symptom**: `_check_excluded_company` checks both "the excluded name is contained in the company name" and "the company name is contained in the excluded name", by characters rather than by words. For example, excluding "Meta" hits "Metaview"; a very short exclusion (e.g. "AI") hits "OpenAI", "Air New Zealand" and many others. Conversely, a very short company name in a job can fall inside a longer excluded name.
- **Possible improvements**: match on word boundaries, or require the shorter side to have a minimum length; add edge-case tests.

### 7. Salaries in different currencies can't be compared (P2)

- **Symptom**: when the job and the preference use different currencies, the result is simply `unknown`, which counts as 50 in P.
- **Possible improvements**: add a fixed exchange-rate table (updated with code releases, to stay deterministic), or let the user set an expectation per currency.

### 8. Match evaluation isn't cached (P2)

- **Symptom**: JD parsing is cached globally by text fingerprint, but match evaluation calls the LLM every time. Re-analysing the same job costs money again, and because scores vary, the result may differ from last time.
- **Possible improvements**: cache evaluation results by (JD fingerprint + profile version), with a "re-evaluate" option to force a refresh.

### 9. Jobs can be analysed with an unconfirmed profile (P2)

- **Symptom**: after uploading a resume without reviewing and confirming it, `/api/jobs/analyze` still works; the report is marked `profile_confirmed: false`.
- **Impact**: parsing errors (like the earlier internship classification problem) feed straight into the scores.
- **Possible improvements**: show a prominent warning in the extension when the profile is unconfirmed, or add a setting that requires confirmation before analysis.

### 10. No automated verification against a real model (P2)

- **Symptom**: all 100 tests use fake LLMs. They ensure the code logic is correct but can't catch broken prompts, provider API changes or changes in the model's output format. The internship classification and name leak problems were both found by hand with a real CV.
- **Handling**: added `backend/tests/test_live.py` (marked `live`, skipped by default), run manually with `.venv/bin/pytest -m live -s`. It covers resume parsing (no name/contact leak, internship classification, injected skills not recorded, languages and awards), normal job analysis, no full marks for the injected job, and 422 for a non-job page.
- **Follow-up**: assertions only check structure and key properties; typical cases from the evaluation set can be added over time.

### 11. Scanned PDFs aren't supported (P3)

- **Symptom**: `pypdf` only extracts the text layer, so scanned or image-only PDFs yield no content.
- **Possible improvements**: detect an empty extraction and show a clear message; later consider OCR (mind the licence and avoid AGPL dependencies) or a multimodal model.

### 12. Auth is a single API key (P3)

- **Symptom**: there is only one `X-API-Key`, suitable for single-user local use.
- **Possible improvements**: introduce user accounts and per-user data isolation in the multi-user phase; how the extension stores the key needs to be considered at the same time.

### 13. The database isn't synced through Git (P3, by design)

- **Symptom**: each machine has its own SQLite database; profiles, preferences and reports aren't shared.
- **Reason**: keeps personal data out of the public repo.
- **Note**: run `.venv/bin/alembic upgrade head` on each machine after pulling. After moving to PostgreSQL in Phase 2, a hosted database could be considered.

### 14. Resume and job content is sent to a third-party LLM (P3, known and accepted)

- **Symptom**: content is sent to Alibaba Cloud DashScope for processing (or to Azure when switched). Data is minimised: contact details aren't extracted, the name is replaced with "the candidate", and match evaluation only sends the structured profile.
- **Possible improvements**: explain this to users in the README / extension; if needed, offer a local-model option (the earlier Ollama attempt was poor on injection resistance and speed).

### 15. Miscellaneous docs and repo to-dos (P3)

- The formula syntax `\[ \]` in the outline should be changed to `$$`.
- Add a LICENSE.

### 16. Closing the side panel loses tasks in progress (P2)

- **Symptom**: while a job is being analysed (about 30 seconds) or a resume uploaded (10–60 seconds), closing the side panel or reloading the extension from the extensions page loses the page state, and reopening it shows neither progress nor result. Switching tabs inside the side panel isn't affected (fixed on 2026-10-19: every page stays mounted and tabs with work in progress show a spinner).
- **Impact**: the backend still finishes and saves the analysis, which can be found in History, but the user can't tell whether the task is still running and may click again, causing duplicate LLM calls and costs. Resume upload results are saved too and appear when the Resume page is reopened.
- **Location**: `extension/src/sidepanel/AnalyzeView.tsx`, `ProfileView.tsx` (requests start in the side-panel page and their state only lives in React components).
- **Possible improvements**:
  - Move requests to the background service worker and write task state (in progress / result / error, per tab) to `chrome.storage.session`; the side panel reads it and subscribes to changes when opened.
  - Note that an MV3 service worker is terminated after about 30 seconds idle; check that it isn't reclaimed during a long `fetch` (Chrome 116+ is more lenient), and use a keepalive or switch to async backend tasks + polling if needed.
  - Backend async option: `POST /api/jobs/analyze` immediately returns a task ID and the extension polls for status; more robust, and helpful for batch analysis later.
