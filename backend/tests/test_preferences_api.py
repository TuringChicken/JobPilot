import pytest


def test_requires_api_key(client):
    assert client.get("/api/preferences", headers={"X-API-Key": ""}).status_code == 401
    assert client.patch("/api/preferences", json={}, headers={"X-API-Key": ""}).status_code == 401


def test_get_before_save_returns_empty_defaults(client):
    resp = client.get("/api/preferences")
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_roles"] == []
    assert body["min_salary"] is None
    assert body["salary_currency"] == "NZD"
    assert body["updated_at"] is None


def test_patch_creates_then_merges_partial_updates(client):
    first = client.patch(
        "/api/preferences",
        json={"target_roles": ["AI Engineer"], "locations": ["Auckland"], "min_salary": 70000},
    )
    assert first.status_code == 200
    assert first.json()["updated_at"] is not None

    second = client.patch("/api/preferences", json={"work_arrangements": ["hybrid", "remote"]})
    body = second.json()
    assert body["target_roles"] == ["AI Engineer"]
    assert body["locations"] == ["Auckland"]
    assert body["min_salary"] == 70000
    assert body["work_arrangements"] == ["hybrid", "remote"]

    assert client.get("/api/preferences").json() == body


def test_patch_normalizes_text(client):
    body = client.patch(
        "/api/preferences",
        json={
            "target_roles": ["  AI Engineer ", "ai engineer", "Python Developer"],
            "experience_levels": ["junior", "junior", "graduate"],
            "salary_currency": "aud",
        },
    ).json()
    assert body["target_roles"] == ["AI Engineer", "Python Developer"]
    assert body["experience_levels"] == ["junior", "graduate"]
    assert body["salary_currency"] == "AUD"


def test_explicit_null_clears_nullable_field(client):
    client.patch("/api/preferences", json={"min_salary": 70000})
    body = client.patch("/api/preferences", json={"min_salary": None}).json()
    assert body["min_salary"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"work_arrangements": ["office"]},
        {"experience_levels": ["principal"]},
        {"min_salary": -1},
        {"salary_currency": "dollars"},
        {"salary_period": "month"},
        {"target_roles": [""]},
        {"target_roles": ["x" * 101]},
        {"locations": [f"City {i}" for i in range(21)]},
        {"target_roles": None},
        {"unknown_field": 1},
    ],
)
def test_patch_rejects_invalid_values(client, payload):
    assert client.patch("/api/preferences", json=payload).status_code == 422


def test_invalid_patch_does_not_change_saved_preferences(client):
    saved = client.patch("/api/preferences", json={"target_roles": ["AI Engineer"]}).json()
    client.patch("/api/preferences", json={"target_roles": ["Data Scientist"], "min_salary": -5})
    assert client.get("/api/preferences").json() == saved


def test_delete_resets_to_defaults(client):
    client.patch("/api/preferences", json={"target_roles": ["AI Engineer"]})
    assert client.delete("/api/preferences").status_code == 204
    body = client.get("/api/preferences").json()
    assert body["target_roles"] == []
    assert body["updated_at"] is None
