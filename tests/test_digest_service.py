import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.models import Topic
from app.services.digest_service import DigestService
from app.services.sources.base import SourceComment, SourcePost
from app.services.summarizer import Consensus, HotTopic


class FakeSource:
    name = "Fake"

    def __init__(self, posts, comments):
        self._posts = posts
        self._comments = comments

    def top_posts(self, query, limit=None):
        return self._posts

    def top_comments(self, query, post_id, limit=None):
        return self._comments.get(post_id, [])

    def close(self):
        pass


class FakeSummarizer:
    def summarize(self, query, posts, comments=None):
        return Consensus(
            overview="overview text",
            hot_topics=[HotTopic(title="t1", summary="s1")],
        )


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_get_for_topic_generates_and_caches(session):
    topic = Topic(slug="python", display_name="Python", query="python")
    session.add(topic)
    session.commit()

    posts = [
        SourcePost(
            id="abc",
            title="First post",
            author="alice",
            score=100,
            num_comments=10,
            permalink="https://news.ycombinator.com/item?id=abc",
            url="https://example.com/abc",
            selftext="hello",
        ),
    ]
    comments = {"abc": [SourceComment(author="carol", body="great", score=20)]}
    source = FakeSource(posts, comments)
    service = DigestService(session, source=source, summarizer=FakeSummarizer())

    _, digest, cached = service.get_for_topic("python")
    assert cached is False
    assert digest.overview == "overview text"
    assert len(digest.posts) == 1
    assert digest.posts[0].source_id == "abc"

    _, digest2, cached2 = service.get_for_topic("python")
    assert cached2 is True
    assert digest2.id == digest.id
