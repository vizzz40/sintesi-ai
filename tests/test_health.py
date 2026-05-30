from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_index_serves_page():
    res = client.get("/")
    assert res.status_code == 200
    assert "Sintesi" in res.text
