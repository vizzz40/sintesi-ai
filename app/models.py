from datetime import UTC, date, datetime

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class Topic(SQLModel, table=True):
    __tablename__ = "topics"

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    display_name: str
    subreddit: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Digest(SQLModel, table=True):
    __tablename__ = "digests"
    __table_args__ = (UniqueConstraint("subreddit", "digest_date"),)

    id: int | None = Field(default=None, primary_key=True)
    subreddit: str = Field(index=True)
    digest_date: date
    overview: str
    hot_topics: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    model_used: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    posts: list["Post"] = Relationship(
        back_populates="digest",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: int | None = Field(default=None, primary_key=True)
    digest_id: int = Field(foreign_key="digests.id")
    reddit_id: str
    title: str
    url: str
    permalink: str
    score: int
    num_comments: int
    author: str
    rank: int

    digest: Digest | None = Relationship(back_populates="posts")
