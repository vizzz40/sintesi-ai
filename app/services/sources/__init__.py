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
    return HackerNewsSource(settings)
