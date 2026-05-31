from datetime import date, datetime

from pydantic import BaseModel


class TopicOut(BaseModel):
    slug: str
    display_name: str
    query: str


class HotTopicOut(BaseModel):
    title: str
    summary: str


class PostOut(BaseModel):
    title: str
    url: str
    permalink: str
    score: int
    num_comments: int


class DigestOut(BaseModel):
    topic: str | None
    source: str
    query: str
    date: date
    overview: str
    hot_topics: list[HotTopicOut]
    top_posts: list[PostOut]
    model_used: str
    generated_at: datetime
    cached: bool
