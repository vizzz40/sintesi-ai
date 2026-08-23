from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db import get_session
from app.models import Digest, Topic
from app.schemas import DigestOut, PostOut, TopicOut
from app.services.digest_service import DigestService, NoResults, TopicNotFound
from app.services.sources import SourceError
from app.services.summarizer import SummarizerError

router = APIRouter(prefix="/api")

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/config")
def get_public_config(settings: SettingsDep):
    return {"allow_freeform_search": settings.allow_freeform_search}


@router.get("/topics", response_model=list[TopicOut])
def list_topics(session: SessionDep):
    topics = session.exec(select(Topic).order_by(Topic.display_name)).all()
    return [TopicOut(slug=t.slug, display_name=t.display_name, query=t.query) for t in topics]


@router.get("/digest/{slug}", response_model=DigestOut)
def get_digest(slug: str, session: SessionDep, refresh: bool = False):
    service = DigestService(session)
    try:
        topic, digest, cached = service.get_for_topic(slug, refresh)
    except TopicNotFound:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {slug}") from None
    except NoResults:
        raise HTTPException(status_code=404, detail="No recent discussion to summarize") from None
    except SourceError:
        raise HTTPException(
            status_code=502, detail="Could not fetch posts from the source"
        ) from None
    except SummarizerError:
        raise HTTPException(status_code=502, detail="Could not generate the summary") from None
    finally:
        service.close()
    return _to_out(topic, digest, cached, service.source.name)


@router.get("/search", response_model=DigestOut)
def search(q: str, session: SessionDep, settings: SettingsDep, refresh: bool = False):
    if not settings.allow_freeform_search:
        raise HTTPException(
            status_code=403,
            detail="Free-form search is disabled on the public demo. Choose a curated topic.",
        )
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Type a topic to search for")
    if len(query) > 100:
        query = query[:100]
    service = DigestService(session)
    try:
        topic, digest, cached = service.get_for_query(query, refresh)
    except NoResults:
        raise HTTPException(
            status_code=404, detail=f'No recent Hacker News discussion about "{query}"'
        ) from None
    except SourceError:
        raise HTTPException(
            status_code=502, detail="Could not fetch posts from the source"
        ) from None
    except SummarizerError:
        raise HTTPException(status_code=502, detail="Could not generate the summary") from None
    finally:
        service.close()
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
