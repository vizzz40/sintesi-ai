from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class SourceError(Exception):
    pass


class SourcePost(BaseModel):
    id: str
    title: str
    author: str
    score: int
    num_comments: int
    permalink: str
    url: str
    selftext: str = ""


class SourceComment(BaseModel):
    author: str
    body: str
    score: int


@runtime_checkable
class ContentSource(Protocol):
    name: str

    def top_posts(self, query: str, limit: int | None = None) -> list[SourcePost]: ...

    def top_comments(
        self, query: str, post_id: str, limit: int | None = None
    ) -> list[SourceComment]: ...

    def close(self) -> None: ...
