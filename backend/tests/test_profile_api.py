from tests.conftest import make_docx, make_pdf

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def upload(client, filename="cv.docx", content=None, content_type=DOCX_TYPE):
    content = make_docx() if content is None else content
    return client.post("/api/profile/resume", files={"file": (filename, content, content_type)})


def test_health_needs_no_auth(client):
    resp = client.get("/api/health", headers={"X-API-Key": ""})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_rejects_missing_or_wrong_api_key(client):
    assert client.get("/api/profile", headers={"X-API-Key": ""}).status_code == 401
    assert client.get("/api/profile", headers={"X-API-Key": "wrong"}).status_code == 401


def test_get_profile_before_upload_returns_404(client):
    assert client.get("/api/profile").status_code == 404


def test_upload_docx_creates_unconfirmed_profile(client, fake_parser):
    resp = upload(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["confirmed"] is False
    assert body["resume_filename"] == "cv.docx"
    assert body["data"]["skills"][0]["name"] == "Python"
    assert "Docker, PostgreSQL" in fake_parser.calls[0]

    assert client.get("/api/profile").json()["id"] == body["id"]


def test_upload_pdf_passes_extracted_text_to_parser(client, fake_parser):
    resp = upload(client, "cv.pdf", make_pdf(), "application/pdf")
    assert resp.status_code == 200
    assert "FastAPI" in fake_parser.calls[0]


def test_reupload_replaces_profile_and_resets_confirmation(client):
    first = upload(client).json()
    client.patch("/api/profile", json={"confirmed": True})
    second = upload(client, "cv.pdf", make_pdf(), "application/pdf").json()
    assert second["id"] == first["id"]
    assert second["resume_filename"] == "cv.pdf"
    assert second["confirmed"] is False


def test_rejects_unsupported_type(client):
    assert upload(client, "cv.txt", b"x" * 100, "text/plain").status_code == 415


def test_rejects_oversize_file(client, settings):
    big = b"%PDF" + b"0" * settings.max_resume_bytes
    assert upload(client, "cv.pdf", big, "application/pdf").status_code == 413


def test_rejects_unreadable_resume(client, fake_parser):
    resp = upload(client, "cv.pdf", make_pdf("Hi"), "application/pdf")
    assert resp.status_code == 422
    assert fake_parser.calls == []


def test_patch_updates_data_and_confirms(client):
    data = upload(client).json()["data"]
    data["skills"].append({"name": "Azure", "category": "cloud", "proficiency": None})

    resp = client.patch("/api/profile", json={"data": data, "confirmed": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["confirmed"] is True
    assert [s["name"] for s in body["data"]["skills"]] == ["Python", "Azure"]


def test_patch_rejects_invalid_data(client):
    upload(client)
    resp = client.patch("/api/profile", json={"data": {"skills": "not a list"}})
    assert resp.status_code == 422


def test_delete_profile(client):
    upload(client)
    assert client.delete("/api/profile").status_code == 204
    assert client.get("/api/profile").status_code == 404


def test_upload_without_llm_configured_returns_503(client):
    client.app.dependency_overrides.clear()
    assert upload(client).status_code == 503
