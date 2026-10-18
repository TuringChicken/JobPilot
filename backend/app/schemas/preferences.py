from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, create_model, field_validator

# Bounded so preferences stay small enough to embed in every match prompt.
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TextList = Annotated[list[ShortText], Field(max_length=20)]

WorkArrangement = Literal["onsite", "hybrid", "remote"]
EmploymentType = Literal["full_time", "part_time", "contract", "internship", "temporary"]
ExperienceLevel = Literal["intern", "graduate", "junior", "mid", "senior", "lead"]


class JobPreferencesData(BaseModel):
    """Job-search preferences. Empty lists mean "no restriction"."""

    model_config = ConfigDict(extra="forbid")

    target_roles: TextList = []
    locations: TextList = []
    work_arrangements: list[WorkArrangement] = []
    employment_types: list[EmploymentType] = []
    experience_levels: list[ExperienceLevel] = []

    min_salary: int | None = Field(default=None, ge=0, le=10_000_000)
    salary_currency: Annotated[
        # Pydantic checks the pattern before to_upper, so accept either case here.
        str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{3}$")
    ] = "NZD"
    salary_period: Literal["year", "hour"] = "year"

    # Conditions a job must satisfy, e.g. "visa sponsorship available".
    must_haves: TextList = []
    # Conditions that rule a job out, e.g. "requires NZ citizenship", "on-call rotation".
    deal_breakers: TextList = []
    excluded_companies: TextList = []

    @field_validator("*", mode="after")
    @classmethod
    def _dedupe_lists(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value
        seen: set[str] = set()
        result = []
        for item in value:
            key = item.casefold()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result


# Every field optional with no default, so PATCH can tell "omitted" from "set to null".
# Constraints are re-checked by validating the merged result as JobPreferencesData.
JobPreferencesPatch = create_model(
    "JobPreferencesPatch",
    __config__=ConfigDict(extra="forbid"),
    **{
        name: (field.annotation | None, None)
        for name, field in JobPreferencesData.model_fields.items()
    },
)


class PreferencesOut(JobPreferencesData):
    # None until the user saves preferences for the first time.
    updated_at: datetime | None = None
