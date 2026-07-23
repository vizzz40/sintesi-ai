import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.db import get_session
from app.main import app
from app.services import digest_service
from app.services.sources.base import SourceComment, SourceError, SourcePost
from app.services.summarizer import Consensus, HotTopic


class FakeSource:
    name = "Hacker News"

    def __init__(self, *args, **kwargs):
        pass

    def top_posts(self, query, limit=None):
        return [
            SourcePost(
                id="abc",
                title="Best ETL tools",
                author="dataguy",
                score=420,
                num_comments=37,
                permalink="https://news.ycombinator.com/item?id=abc",
                url="https://example.com/abc",
                selftext="",
            )
        ]

    def top_comments(self, query, post_id, limit=None):
        return [SourceComment(author="a", body="use dbt", score=90)]

    def close(self):
        pass


class FakeSummarizer:
    def __init__(self, *args, **kwargs):
        pass

    def summarize(self, query, posts, comments=None):
        return Consensus(
            overview="People recommend dbt.",
            hot_topics=[HotTopic(title="dbt", summary="Widely recommended.")],
        )


@pytest.fixture
def client(session, monkeypatch):
    monkeypatch.setattr(digest_service, "get_source", lambda *a, **k: FakeSource())
    monkeypatch.setattr(digest_service, "Summarizer", FakeSummarizer)
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_topics(client):
    res = client.get("/api/topics")

    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["slug"] == "data-engineering"


def test_digest_happy_path(client):
    res = client.get("/api/digest/data-engineering")

    assert res.status_code == 200
    body = res.json()
    assert body["overview"] == "People recommend dbt."
    assert body["source"] == "Hacker News"
    assert body["cached"] is False
    assert body["hot_topics"][0]["title"] == "dbt"
    assert body["top_posts"][0]["score"] == 420


def test_digest_is_cached_on_second_call(client):
    client.get("/api/digest/data-engineering")
    res = client.get("/api/digest/data-engineering")

    assert res.json()["cached"] is True


def test_unknown_topic_returns_404(client):
    res = client.get("/api/digest/nope")

    assert res.status_code == 404


def test_source_failure_returns_502(client, monkeypatch):
    def boom(self, query, limit=None):
        raise SourceError("rate limited")

    monkeypatch.setattr(FakeSource, "top_posts", boom)

    res = client.get("/api/digest/data-engineering")

    assert res.status_code == 502


def test_search_returns_digest_for_any_query(client):
    res = client.get("/api/search", params={"q": "rust async"})

    assert res.status_code == 200
    body = res.json()
    assert body["query"] == "rust async"
    assert body["overview"] == "People recommend dbt."
    assert body["cached"] is False


def test_search_is_cached_on_second_call(client):
    client.get("/api/search", params={"q": "rust async"})
    res = client.get("/api/search", params={"q": "rust async"})

    assert res.json()["cached"] is True


def test_search_blank_query_returns_400(client):
    res = client.get("/api/search", params={"q": "   "})

    assert res.status_code == 400


def test_public_config_reports_freeform_search(client):
    res = client.get("/api/config")

    assert res.status_code == 200
    assert res.json() == {"allow_freeform_search": True}


def test_search_can_be_disabled_for_public_demo(client):
    app.dependency_overrides[get_settings] = lambda: Settings(
        allow_freeform_search=False
    )

    res = client.get("/api/search", params={"q": "rust async"})

    assert res.status_code == 403
    assert "public demo" in res.json()["detail"]


def test_search_no_results_returns_404(client, monkeypatch):
    monkeypatch.setattr(FakeSource, "top_posts", lambda self, query, limit=None: [])

    res = client.get("/api/search", params={"q": "nothing here"})

    assert res.status_code == 404
