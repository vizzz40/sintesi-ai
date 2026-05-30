import pytest

from app.services.digest_service import DigestService, TopicNotFound
from app.services.reddit_client import RedditComment, RedditPost
from app.services.summarizer import Consensus, HotTopic


class FakeReddit:
    def __init__(self):
        self.post_calls = 0

    def top_posts(self, subreddit, limit=None):
        self.post_calls += 1
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
    def __init__(self):
        self.calls = 0

    def summarize(self, subreddit, posts, comments=None):
        self.calls += 1
        return Consensus(
            overview="People recommend dbt.",
            hot_topics=[HotTopic(title="dbt", summary="Widely recommended.")],
        )


def make_service(session):
    return DigestService(session, reddit=FakeReddit(), summarizer=FakeSummarizer())


def test_cache_miss_generates_and_persists(session):
    service = make_service(session)

    topic, digest, cached = service.get_for_topic("data-engineering")

    assert cached is False
    assert digest.overview == "People recommend dbt."
    assert digest.id is not None
    assert len(digest.posts) == 1
    assert digest.posts[0].reddit_id == "abc"


def test_second_call_is_cached(session):
    service = make_service(session)

    service.get_for_topic("data-engineering")
    _, _, cached = service.get_for_topic("data-engineering")

    assert cached is True
    assert service.summarizer.calls == 1
    assert service.reddit.post_calls == 1


def test_refresh_regenerates(session):
    service = make_service(session)

    service.get_for_topic("data-engineering")
    _, _, cached = service.get_for_topic("data-engineering", refresh=True)

    assert cached is False
    assert service.summarizer.calls == 2


def test_unknown_topic_raises(session):
    service = make_service(session)

    with pytest.raises(TopicNotFound):
        service.get_for_topic("does-not-exist")
