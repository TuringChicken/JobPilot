import json
from types import SimpleNamespace

from app.schemas.profile import Award, CandidateProfileData, Language, Project, WorkExperience
from app.services.llm import StructuredLLM
from app.services.resume_parser import INSTRUCTIONS, LLMResumeParser, redact_name


def make_profile(**overrides) -> CandidateProfileData:
    fields = dict(
        summary=None,
        education=[],
        skills=[],
        certifications=[],
        languages=[],
        awards=[],
        work_experience=[],
        projects=[],
    )
    return CandidateProfileData(**(fields | overrides))


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content, self.kwargs = content, None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def parse_with(output: dict) -> tuple[CandidateProfileData, FakeCompletions]:
    completions = FakeCompletions(json.dumps(output))
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    parser = LLMResumeParser(StructuredLLM(client, "test-model", json_schema_mode=False))
    return parser.parse("Jane Doe\nPython developer"), completions


def llm_output(**overrides) -> dict:
    return make_profile().model_dump() | {"candidate_name": "Jane Doe"} | overrides


# --- parser ---


def test_parser_drops_candidate_name_and_redacts_it():
    data, _ = parse_with(
        llm_output(
            summary="Jane Doe is a Python developer.",
            projects=[
                {
                    "name": "Thesis project",
                    "description": "Team project where Jane Doe owned the pipeline.",
                    "tech_stack": ["Python"],
                    "outcomes": [],
                }
            ],
        )
    )
    assert "candidate_name" not in data.model_dump()
    assert data.summary == "The candidate is a Python developer."
    assert data.projects[0].description == "Team project where the candidate owned the pipeline."


def test_parser_asks_for_name_internships_languages_and_awards():
    _, completions = parse_with(llm_output())
    system = completions.kwargs["messages"][0]["content"]
    assert system.startswith(INSTRUCTIONS)
    for field in ("candidate_name", "languages", "awards"):
        assert f'"{field}"' in system
    assert "Internships" in INSTRUCTIONS


def test_parser_keeps_languages_and_awards():
    data, _ = parse_with(
        llm_output(
            candidate_name=None,
            languages=[{"name": "English", "proficiency": "IELTS 6.5"}],
            awards=[{"title": "National Second Prize", "issuer": None, "date": None}],
        )
    )
    assert data.languages == [Language(name="English", proficiency="IELTS 6.5")]
    assert data.awards == [Award(title="National Second Prize", issuer=None, date=None)]


# --- redact_name ---


def test_redacts_full_name_in_either_order_and_any_case():
    profile = make_profile(summary="Built by Li Xiaoming. XIAOMING LI's work.")
    assert redact_name(profile, "Xiaoming Li").summary == (
        "Built by the candidate. the candidate's work."
    )


def test_redacts_name_parts_but_not_short_ones():
    profile = make_profile(summary="Xiaoming led it. Li was helpful. Linear algebra.")
    assert redact_name(profile, "Xiaoming Li").summary == (
        "The candidate led it. Li was helpful. Linear algebra."
    )


def test_name_parts_match_case_sensitively():
    profile = make_profile(summary="Will lead teams and will mentor.")
    assert redact_name(profile, "Will Smith").summary == "The candidate lead teams and will mentor."


def test_redacts_nested_fields():
    profile = make_profile(
        work_experience=[
            WorkExperience(
                title="Intern",
                company="Acme",
                start_date="Mar 2021",
                end_date="Jun 2021",
                responsibilities=["Jane Doe built APIs."],
            )
        ],
        projects=[Project(name="Jane's app", description=None, tech_stack=[], outcomes=[])],
    )
    redacted = redact_name(profile, "Jane Doe")
    assert redacted.work_experience[0].responsibilities == ["The candidate built APIs."]
    assert redacted.projects[0].name == "The candidate's app"


def test_no_name_leaves_profile_unchanged():
    profile = make_profile(summary="Python developer")
    assert redact_name(profile, None) == profile
    assert redact_name(profile, "  ") == profile
