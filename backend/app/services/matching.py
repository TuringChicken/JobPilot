"""Deterministic half of matching: hard filters, preference score, evidence checks, totals.

The LLM only supplies per-dimension judgements and quotes; everything that can be decided
by plain rules is decided here so it is reproducible and testable.
"""

import re
import unicodedata
from collections.abc import Iterable

from app.schemas.jobs import (
    CheckStatus,
    ConditionCheck,
    DimensionAssessment,
    DimensionScore,
    Evidence,
    FilterCheck,
    HardFilterResult,
    JobPostingData,
    MatchEvaluation,
    MatchReport,
    VerifiedEvidence,
    VerifiedSkillMatch,
)
from app.schemas.preferences import JobPreferencesData
from app.schemas.profile import CandidateProfileData

# Initial weights from the design doc (section 6.2); to be calibrated on labelled samples.
WEIGHTS = {"skills": 0.35, "experience": 0.25, "responsibilities": 0.20, "preferences": 0.20}
_STATUS_POINTS = {"pass": 100, "unknown": 50, "fail": 0}
HOURS_PER_YEAR = 2080


# --- Hard filters ---


def run_hard_filter(
    prefs: JobPreferencesData, job: JobPostingData, condition_checks: list[ConditionCheck]
) -> HardFilterResult:
    """Check the job against each preference the user actually set.

    Missing job information yields "unknown", never "fail": a posting that doesn't mention
    salary hasn't failed the salary check.
    """
    checks = [
        c
        for c in (
            _check_location(prefs, job),
            _check_choice("work_arrangement", prefs.work_arrangements, job.work_arrangement),
            _check_choice("employment_type", prefs.employment_types, job.employment_type),
            _check_choice("experience_level", prefs.experience_levels, job.experience_level),
            _check_salary(prefs, job),
            _check_excluded_company(prefs, job),
        )
        if c is not None
    ]
    checks += _check_conditions(prefs.must_haves, "must_have", condition_checks)
    checks += _check_conditions(prefs.deal_breakers, "deal_breaker", condition_checks)

    statuses = {c.status for c in checks}
    if "fail" in statuses:
        status = "fail"
    elif "unknown" in statuses:
        status = "needs_review"
    else:
        status = "pass"
    return HardFilterResult(status=status, checks=checks)


def _check_location(prefs: JobPreferencesData, job: JobPostingData) -> FilterCheck | None:
    if not prefs.locations:
        return None
    if job.work_arrangement == "remote" and (
        not prefs.work_arrangements or "remote" in prefs.work_arrangements
    ):
        return FilterCheck(name="location", status="pass", detail="Remote role")
    if not job.location:
        return FilterCheck(name="location", status="unknown", detail="Location not stated")
    job_loc = job.location.casefold()
    hit = next((loc for loc in prefs.locations if loc.casefold() in job_loc), None)
    if hit:
        return FilterCheck(name="location", status="pass", detail=f"{job.location} ({hit})")
    return FilterCheck(
        name="location",
        status="fail",
        detail=f"{job.location} not in {', '.join(prefs.locations)}",
    )


def _check_choice(name: str, wanted: list[str], actual: str | None) -> FilterCheck | None:
    if not wanted:
        return None
    if actual is None:
        return FilterCheck(name=name, status="unknown", detail="Not stated in posting")
    status: CheckStatus = "pass" if actual in wanted else "fail"
    return FilterCheck(name=name, status=status, detail=f"{actual} (wanted: {', '.join(wanted)})")


def _check_salary(prefs: JobPreferencesData, job: JobPostingData) -> FilterCheck | None:
    if prefs.min_salary is None:
        return None
    offered = job.salary_max if job.salary_max is not None else job.salary_min
    if offered is None:
        return FilterCheck(name="salary", status="unknown", detail="Salary not stated")
    if job.salary_currency and job.salary_currency.upper() != prefs.salary_currency:
        return FilterCheck(
            name="salary",
            status="unknown",
            detail=f"Posting is in {job.salary_currency}, preference in {prefs.salary_currency}",
        )

    job_period = job.salary_period or prefs.salary_period
    offered_in_pref_period = _convert_salary(offered, job_period, prefs.salary_period)
    status: CheckStatus = "pass" if offered_in_pref_period >= prefs.min_salary else "fail"
    detail = f"Up to {offered:,} per {job_period}"
    if job_period != prefs.salary_period:
        detail += f" (~{offered_in_pref_period:,} per {prefs.salary_period})"
    detail += f"; minimum {prefs.min_salary:,} per {prefs.salary_period}"
    return FilterCheck(name="salary", status=status, detail=detail)


def _convert_salary(amount: int, from_period: str, to_period: str) -> int:
    if from_period == to_period:
        return amount
    if from_period == "hour":
        return amount * HOURS_PER_YEAR
    return round(amount / HOURS_PER_YEAR)


def _check_excluded_company(prefs: JobPreferencesData, job: JobPostingData) -> FilterCheck | None:
    if not prefs.excluded_companies:
        return None
    if not job.company:
        return FilterCheck(name="excluded_company", status="unknown", detail="Company not stated")
    company = job.company.casefold()
    hit = next(
        (c for c in prefs.excluded_companies if c.casefold() in company or company in c.casefold()),
        None,
    )
    if hit:
        return FilterCheck(name="excluded_company", status="fail", detail=f"Excluded: {hit}")
    return FilterCheck(name="excluded_company", status="pass", detail=job.company)


def _check_conditions(
    conditions: list[str], kind: str, llm_checks: list[ConditionCheck]
) -> list[FilterCheck]:
    # Align to the user's own list: LLM entries for conditions the user never set are
    # ignored, and conditions the LLM skipped become "unknown".
    by_condition = {c.condition.strip().casefold(): c for c in llm_checks if c.kind == kind}
    results = []
    for condition in conditions:
        llm = by_condition.get(condition.casefold())
        if llm is None:
            status, detail = "unknown", "Not assessed"
        else:
            status = {"ok": "pass", "violated": "fail", "unknown": "unknown"}[llm.status]
            detail = "; ".join(e.quote for e in llm.evidence) or "No evidence given"
        results.append(FilterCheck(name=f"{kind}: {condition}", status=status, detail=detail))
    return results


def preference_score(hard_filter: HardFilterResult) -> int:
    if not hard_filter.checks:
        return 100  # No preferences set: nothing to violate.
    points = [_STATUS_POINTS[c.status] for c in hard_filter.checks]
    return round(sum(points) / len(points))


# --- Evidence verification ---


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[\"'`‘’“”…]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,;:-")


def _collect_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _collect_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _collect_strings(v)


class EvidenceVerifier:
    """Checks that quotes really occur in their claimed source."""

    MIN_QUOTE_CHARS = 3

    def __init__(self, profile: CandidateProfileData, job_text: str) -> None:
        self._corpus = {
            "cv": _normalize("\n".join(_collect_strings(profile.model_dump()))),
            "jd": _normalize(job_text),
        }

    def verify(self, evidence: list[Evidence]) -> list[VerifiedEvidence]:
        return [
            VerifiedEvidence(
                source=e.source, quote=e.quote, verified=self._is_verified(e.source, e.quote)
            )
            for e in evidence
        ]

    def _is_verified(self, source: str, quote: str) -> bool:
        needle = _normalize(quote)
        return len(needle) >= self.MIN_QUOTE_CHARS and needle in self._corpus[source]


# --- Report ---


def build_report(
    profile: CandidateProfileData,
    profile_confirmed: bool,
    prefs: JobPreferencesData,
    job: JobPostingData,
    job_text: str,
    job_text_truncated: bool,
    evaluation: MatchEvaluation,
) -> MatchReport:
    verifier = EvidenceVerifier(profile, job_text)
    hard_filter = run_hard_filter(prefs, job, evaluation.condition_checks)

    def llm_dimension(name: str, assessment: DimensionAssessment) -> DimensionScore:
        return DimensionScore(
            score=_clamp(assessment.score),
            weight=WEIGHTS[name],
            rationale=assessment.rationale,
            evidence=verifier.verify(assessment.evidence),
        )

    dims = {
        "skills": llm_dimension("skills", evaluation.skills),
        "experience": llm_dimension("experience", evaluation.experience),
        "responsibilities": llm_dimension("responsibilities", evaluation.responsibilities),
        "preferences": DimensionScore(
            score=preference_score(hard_filter),
            weight=WEIGHTS["preferences"],
            rationale=_preference_rationale(hard_filter),
            evidence=[],
        ),
    }
    matched = [
        VerifiedSkillMatch(skill=m.skill, evidence=verifier.verify(m.evidence))
        for m in evaluation.matched_skills
    ]
    all_evidence = [e for d in dims.values() for e in d.evidence] + [
        e for m in matched for e in m.evidence
    ]

    return MatchReport(
        overall_score=round(sum(d.score * d.weight for d in dims.values())),
        **dims,
        hard_filter=hard_filter,
        matched_skills=matched,
        missing_skills=evaluation.missing_skills,
        uncertainties=evaluation.uncertainties,
        unverified_evidence_count=sum(not e.verified for e in all_evidence),
        profile_confirmed=profile_confirmed,
        job_text_truncated=job_text_truncated,
    )


def _clamp(score: int) -> int:
    return max(0, min(100, score))


def _preference_rationale(hard_filter: HardFilterResult) -> str:
    if not hard_filter.checks:
        return "No preferences set."
    counts = {
        s: sum(c.status == s for c in hard_filter.checks) for s in ("pass", "fail", "unknown")
    }
    return (
        f"{counts['pass']} passed, {counts['fail']} failed, {counts['unknown']} unknown "
        f"of {len(hard_filter.checks)} preference checks."
    )
