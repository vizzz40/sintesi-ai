from app.config import Settings, get_settings
from app.services.sources.base import (
    ContentSource,
    SourceComment,
    SourceError,
    SourcePost,
)
from app.services.sources.hackernews import HackerNewsSource

__all__ = [
    "ContentSource",
    "SourceComment",
    "SourceError",
    "SourcePost",
    "get_source",
]


def get_source(settings: Settings | None = None) -> ContentSource:
    settings = settings or get_settings()
    name = settings.content_source.lower()
    if name == "hackernews":
        return HackerNewsSource(settings)
    if name == "reddit":
        from app.services.reddit_client import RedditClient

        return RedditClient(settings)
    raise SourceError(f"Unknown content source: {settings.content_source}")
