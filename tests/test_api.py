import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.services import digest_service
from app.services.reddit_client import RedditComment, RedditError, RedditPost
from app.services.summarizer import Consensus, HotTopic


class FakeReddit:
    def __init__(self, *args, **kwargs):
        pass

    def top_posts(self, subreddit, limit=None):
        return [
            RedditPost(
                id="abc",
                title="Best ETL tools",
                author="dataguy",
                score=420,
                num_comments=37,
                permalink="/r/dataengineering/comments/abc/",
                url="https://reddit.com/abc",
                selftext="",
            )
        ]

    def top_comments(self, subreddit, post_id, limit=None):
        return [RedditComment(author="a", body="use dbt", score=90)]


class FakeSummarizer:
    def __init__(self, *args, **kwargs):
        pass

    def summarize(self, subreddit, posts, comments=None):
        return Consensus(
            overview="People recommend dbt.",
            hot_topics=[HotTopic(title="dbt", summary="Widely recommended.")],
        )


@pytest.fixture
def client(session, monkeypatch):
    monkeypatch.setattr(digest_service, "RedditClient", FakeReddit)
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


def test_reddit_failure_returns_502(client, monkeypatch):
    def boom(self, subreddit, limit=None):
        raise RedditError("rate limited")

    monkeypatch.setattr(FakeReddit, "top_posts", boom)

    res = client.get("/api/digest/data-engineering")

    assert res.status_code == 502
