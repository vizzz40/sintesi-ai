import html
import re
import time

import httpx

from app.config import Settings, get_settings
from app.services.sources.base import SourceComment, SourceError, SourcePost

_TAG = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    text = text.replace("</p><p>", "\n\n").replace("<p>", "\n\n")
    return html.unescape(_TAG.sub("", text)).strip()


class HackerNewsSource:
    """Reads stories and comments from the Hacker News Algolia API."""

    name = "Hacker News"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        self._client = client or httpx.Client(
            base_url=self.settings.hn_base_url, timeout=10.0
        )

    def top_posts(self, query: str, limit: int | None = None) -> list[SourcePost]:
        limit = limit or self.settings.posts_per_digest
        cutoff = int(time.time()) - self.settings.hn_days * 86400
        # Over-fetch the recent matches, then keep the highest-voted ones so the
        # digest reflects what actually drew discussion, not just relevance.
        data = self._get(
            "/api/v1/search",
            params={
                "query": query,
                "tags": "story",
                "hitsPerPage": max(limit * 3, 50),
                "numericFilters": f"created_at_i>{cutoff}",
            },
        )
        posts = [self._parse_post(h) for h in data.get("hits", []) if h.get("title")]
        posts.sort(key=lambda p: p.score, reverse=True)
        return posts[:limit]

    def top_comments(
        self, query: str, post_id: str, limit: int | None = None
    ) -> list[SourceComment]:
        limit = limit or self.settings.comments_per_post
        data = self._get(f"/api/v1/items/{post_id}", params={})
        comments = []
        for child in data.get("children", []):
            if not child.get("text") or not child.get("author"):
                continue
            comments.append(self._parse_comment(child))
            if len(comments) >= limit:
                break
        return comments

    def _parse_post(self, h: dict) -> SourcePost:
        object_id = str(h["objectID"])
        permalink = f"https://news.ycombinator.com/item?id={object_id}"
        return SourcePost(
            id=object_id,
            title=h.get("title", ""),
            author=h.get("author", "[unknown]"),
            score=h.get("points") or 0,
            num_comments=h.get("num_comments") or 0,
            permalink=permalink,
            url=h.get("url") or permalink,
            selftext=_strip_html(h.get("story_text") or ""),
        )

    def _parse_comment(self, c: dict) -> SourceComment:
        return SourceComment(
            author=c.get("author") or "[unknown]",
            body=_strip_html(c.get("text") or ""),
            score=c.get("points") or 0,
        )

    def _get(self, path: str, params: dict) -> dict:
        try:
            res = self._client.get(path, params=params)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            raise SourceError(
                f"Hacker News returned {e.response.status_code} for {path}"
            ) from e
        except httpx.HTTPError as e:
            raise SourceError(f"Could not reach Hacker News for {path}") from e

    def close(self) -> None:
        self._client.close()
