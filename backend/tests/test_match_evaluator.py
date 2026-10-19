from app.schemas.preferences import JobPreferencesData
from app.services.match_evaluator import LLMMatchEvaluator, language_name
from tests.conftest import FakeResumeParser, make_evaluation, make_job_data


class CapturingLLM:
    def __init__(self) -> None:
        self.instructions = ""

    def parse(self, instructions, content, schema):
        self.instructions = instructions
        return make_evaluation()


def evaluate(language: str) -> str:
    llm = CapturingLLM()
    profile = FakeResumeParser().parse("")
    LLMMatchEvaluator(llm).evaluate(
        profile, JobPreferencesData(), make_job_data(), "job text", language
    )
    return llm.instructions


def test_prompt_asks_for_report_language_and_verbatim_quotes():
    instructions = evaluate("zh-CN")
    assert "in Simplified Chinese" in instructions
    assert "verbatim in their original language" in instructions
    assert "in English" in evaluate("en")


def test_language_names():
    assert language_name("ZH-cn") == "Simplified Chinese"
    assert language_name("ja") == "the language with BCP 47 tag 'ja'"
