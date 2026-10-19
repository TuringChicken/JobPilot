from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.preferences import EmploymentType, ExperienceLevel, WorkArrangement

# LLM-facing models (JobPostingData, MatchEvaluation and their parts) have no defaults:
# they double as structured-output schemas, where every property must be present.


# --- Request ---


class AnalyzeJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = Field(default=None, max_length=2048)
    page_title: str | None = Field(default=None, max_length=500)
    # Visible page text captured by the extension's content script.
    text: str = Field(min_length=1, max_length=100_000)
    # BCP 47 tag for the report's free-text fields (rationales, notes, uncertainties).
    language: str = Field(
        default="en", max_length=20, pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$"
    )


# --- Step 1: job posting extraction (LLM) ---


class JobPostingData(BaseModel):
    is_job_posting: bool = Field(description="False if the text is not a single job posting")
    title: str | None
    company: str | None
    location: str | None
    work_arrangement: WorkArrangement | None
    employment_type: EmploymentType | None
    experience_level: ExperienceLevel | None
    min_years_experience: int | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None = Field(description="ISO 4217 code, e.g. NZD")
    salary_period: Literal["year", "hour"] | None
    required_skills: list[str]
    preferred_skills: list[str]
    responsibilities: list[str]
    qualifications: list[str]
    work_rights: str | None = Field(description="Visa/citizenship requirement as stated")


# --- Step 2: match evaluation (LLM) ---


class Evidence(BaseModel):
    source: Literal["cv", "jd"]
    quote: str = Field(description="Verbatim excerpt, at most ~200 characters")


class DimensionAssessment(BaseModel):
    score: int = Field(description="0-100")
    rationale: str
    evidence: list[Evidence]


class SkillMatch(BaseModel):
    skill: str
    evidence: list[Evidence]


class SkillGap(BaseModel):
    skill: str
    importance: Literal["required", "preferred"]
    note: str | None


ConditionStatus = Literal["ok", "violated", "unknown"]


class ConditionCheck(BaseModel):
    condition: str = Field(description="The preference condition, copied verbatim")
    kind: Literal["must_have", "deal_breaker"]
    status: ConditionStatus = Field(
        description="ok: must-have satisfied / deal-breaker absent; violated: the opposite; "
        "unknown: the posting does not say"
    )
    evidence: list[Evidence]


class MatchEvaluation(BaseModel):
    skills: DimensionAssessment
    experience: DimensionAssessment
    responsibilities: DimensionAssessment
    matched_skills: list[SkillMatch]
    missing_skills: list[SkillGap]
    condition_checks: list[ConditionCheck]
    uncertainties: list[str]


# --- Report (computed in code) ---

CheckStatus = Literal["pass", "fail", "unknown"]


class FilterCheck(BaseModel):
    name: str
    status: CheckStatus
    detail: str


class HardFilterResult(BaseModel):
    status: Literal["pass", "fail", "needs_review"]
    checks: list[FilterCheck]


class VerifiedEvidence(Evidence):
    # False when the quote can't be found in the CV profile / job text: possibly fabricated.
    verified: bool


class DimensionScore(BaseModel):
    score: int
    weight: float
    rationale: str
    evidence: list[VerifiedEvidence]


class VerifiedSkillMatch(BaseModel):
    skill: str
    evidence: list[VerifiedEvidence]


class MatchReport(BaseModel):
    overall_score: int
    skills: DimensionScore
    experience: DimensionScore
    responsibilities: DimensionScore
    preferences: DimensionScore
    hard_filter: HardFilterResult
    matched_skills: list[VerifiedSkillMatch]
    missing_skills: list[SkillGap]
    uncertainties: list[str]
    unverified_evidence_count: int
    profile_confirmed: bool
    job_text_truncated: bool


# --- API output ---


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str | None
    data: JobPostingData


class MatchOut(BaseModel):
    id: int
    job: JobOut
    report: MatchReport
    saved: bool
    created_at: datetime


class MatchPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    saved: bool


class MatchSummary(BaseModel):
    id: int
    job_id: int
    title: str | None
    company: str | None
    url: str | None
    overall_score: int
    hard_filter_status: str
    saved: bool
    created_at: datetime
