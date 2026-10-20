from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Fields have no defaults on purpose: these models double as the LLM structured-output
# schema, and strict mode requires every property to be present (null when unknown).
# Contact details (name, email, phone, address) are deliberately not extracted.


class Education(BaseModel):
    institution: str
    degree: str | None
    field_of_study: str | None
    start_date: str | None
    end_date: str | None


class Skill(BaseModel):
    name: str
    category: str | None = Field(description="e.g. language, framework, cloud, tool")
    proficiency: Literal["beginner", "intermediate", "advanced", "expert"] | None = Field(
        description="Only if the resume states it explicitly; otherwise null"
    )


class Certification(BaseModel):
    name: str
    issuer: str | None
    date: str | None


class Language(BaseModel):
    name: str
    proficiency: str | None = Field(
        description="As written, e.g. 'native', 'fluent', 'IELTS 6.5'; otherwise null"
    )


class Award(BaseModel):
    title: str
    issuer: str | None
    date: str | None


class WorkExperience(BaseModel):
    title: str
    company: str
    start_date: str | None
    end_date: str | None
    responsibilities: list[str]


class Project(BaseModel):
    name: str
    description: str | None
    tech_stack: list[str]
    outcomes: list[str]


class CandidateProfileData(BaseModel):
    summary: str | None
    work_rights: str | None = Field(
        description="Visa/residency/citizenship status as written, e.g. 'Post Study Work Visa "
        "(valid until 2027)'; null unless the resume states it"
    )
    education: list[Education]
    skills: list[Skill]
    certifications: list[Certification]
    languages: list[Language]
    awards: list[Award]
    work_experience: list[WorkExperience]
    projects: list[Project]


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_filename: str
    confirmed: bool
    data: CandidateProfileData
    updated_at: datetime


class ProfilePatch(BaseModel):
    data: CandidateProfileData | None = None
    confirmed: bool | None = None
