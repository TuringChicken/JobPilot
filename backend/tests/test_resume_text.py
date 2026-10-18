import pytest

from app.services.resume_text import (
    ResumeExtractionError,
    UnsupportedResumeType,
    extract_resume_text,
)
from tests.conftest import make_docx, make_pdf


def test_extracts_pdf_text():
    text = extract_resume_text("cv.pdf", make_pdf())
    assert "FastAPI" in text


def test_extracts_docx_paragraphs_and_tables():
    text = extract_resume_text("cv.DOCX", make_docx())
    assert "FastAPI" in text
    assert "Docker, PostgreSQL" in text


def test_rejects_unsupported_extension():
    with pytest.raises(UnsupportedResumeType):
        extract_resume_text("cv.txt", b"plain text")


def test_rejects_renamed_file():
    with pytest.raises(ResumeExtractionError):
        extract_resume_text("cv.pdf", make_docx())


def test_rejects_resume_without_enough_text():
    with pytest.raises(ResumeExtractionError):
        extract_resume_text("cv.pdf", make_pdf("Hi"))
