from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Digest, Topic
from app.schemas import DigestOut, PostOut, TopicOut
from app.services.digest_service import DigestService, TopicNotFound
from app.services.sources import SourceError
from app.services.summarizer import SummarizerError

router = APIRouter(prefix="/api")

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/topics", response_model=list[TopicOut])
def list_topics(session: SessionDep):
    topics = session.exec(select(Topic).order_by(Topic.display_name)).all()
    return [
        TopicOut(slug=t.slug, display_name=t.display_name, query=t.query)
        for t in topics
    ]


@router.get("/digest/{slug}", response_model=DigestOut)
def get_digest(slug: str, session: SessionDep, refresh: bool = False):
    service = DigestService(session)
    try:
        topic, digest, cached = service.get_for_topic(slug, refresh)
    except TopicNotFound:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {slug}") from None
    except SourceError:
        raise HTTPException(
            status_code=502, detail="Could not fetch posts from the source"
        ) from None
    except SummarizerError:
        raise HTTPException(status_code=502, detail="Could not generate the summary") from None
    return _to_out(topic, digest, cached, service.source.name)


def _to_out(topic: Topic, digest: Digest, cached: bool, source: str) -> DigestOut:
    posts = sorted(digest.posts, key=lambda p: p.rank)
    return DigestOut(
        topic=topic.slug,
        source=source,
        query=digest.query,
        date=digest.digest_date,
        overview=digest.overview,
        hot_topics=digest.hot_topics,
        top_posts=[
            PostOut(
                title=p.title,
                url=p.url,
                permalink=p.permalink,
                score=p.score,
                num_comments=p.num_comments,
            )
            for p in posts
        ],
        model_used=digest.model_used,
        generated_at=digest.generated_at,
        cached=cached,
    )
