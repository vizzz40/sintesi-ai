from datetime import date

from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.models import Digest, Post, Topic
from app.services.reddit_client import RedditClient
from app.services.summarizer import Summarizer


class TopicNotFound(Exception):
    pass


class DigestService:
    def __init__(
        self,
        session: Session,
        reddit: RedditClient | None = None,
        summarizer: Summarizer | None = None,
        settings: Settings | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.reddit = reddit or RedditClient(self.settings)
        self.summarizer = summarizer or Summarizer(self.settings)

    def get_for_topic(self, slug: str, refresh: bool = False) -> tuple[Topic, Digest, bool]:
        topic = self.session.exec(select(Topic).where(Topic.slug == slug)).first()
        if topic is None:
            raise TopicNotFound(slug)
        digest, cached = self._get_or_create(topic.subreddit, refresh)
        return topic, digest, cached

    def _get_or_create(self, subreddit: str, refresh: bool) -> tuple[Digest, bool]:
        today = date.today()
        existing = self.session.exec(
            select(Digest).where(
                Digest.subreddit == subreddit, Digest.digest_date == today
            )
        ).first()
        if existing is not None and not refresh:
            return existing, True
        if existing is not None:
            self.session.delete(existing)
            self.session.commit()
        return self._generate(subreddit, today), False

    def _generate(self, subreddit: str, day: date) -> Digest:
        posts = self.reddit.top_posts(subreddit)
        comments = {
            p.id: self.reddit.top_comments(subreddit, p.id) for p in posts[:5]
        }
        consensus = self.summarizer.summarize(subreddit, posts, comments)

        digest = Digest(
            subreddit=subreddit,
            digest_date=day,
            overview=consensus.overview,
            hot_topics=[t.model_dump() for t in consensus.hot_topics],
            model_used=self.settings.groq_model,
        )
        digest.posts = [
            Post(
                reddit_id=p.id,
                title=p.title,
                url=p.url,
                permalink=p.permalink,
                score=p.score,
                num_comments=p.num_comments,
                author=p.author,
                rank=i,
            )
            for i, p in enumerate(posts)
        ]
        self.session.add(digest)
        self.session.commit()
        self.session.refresh(digest)
        return digest
