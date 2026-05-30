import httpx
from pydantic import BaseModel

from app.config import Settings, get_settings


class RedditError(Exception):
    pass


class RedditPost(BaseModel):
    id: str
    title: str
    author: str
    score: int
    num_comments: int
    permalink: str
    url: str
    selftext: str = ""


class RedditComment(BaseModel):
    author: str
    body: str
    score: int


class RedditClient:
    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self.settings = settings or get_settings()
        self._client = client or httpx.Client(
            base_url=self.settings.reddit_base_url,
            headers={"User-Agent": self.settings.reddit_user_agent},
            timeout=10.0,
        )

    def top_posts(self, subreddit: str, limit: int | None = None) -> list[RedditPost]:
        limit = limit or self.settings.posts_per_digest
        data = self._get(
            f"/r/{subreddit}/top.json",
            params={"t": "day", "limit": limit, "raw_json": 1},
        )
        children = data.get("data", {}).get("children", [])
        return [self._parse_post(c["data"]) for c in children if c.get("kind") == "t3"]

    def top_comments(
        self, subreddit: str, post_id: str, limit: int | None = None
    ) -> list[RedditComment]:
        limit = limit or self.settings.comments_per_post
        data = self._get(
            f"/r/{subreddit}/comments/{post_id}.json",
            params={"sort": "top", "limit": limit, "raw_json": 1},
        )
        if not isinstance(data, list) or len(data) < 2:
            return []
        children = data[1].get("data", {}).get("children", [])
        comments = []
        for c in children:
            if c.get("kind") != "t1":
                continue
            comments.append(self._parse_comment(c["data"]))
            if len(comments) >= limit:
                break
        return comments

    def _parse_post(self, d: dict) -> RedditPost:
        return RedditPost(
            id=d["id"],
            title=d.get("title", ""),
            author=d.get("author", "[deleted]"),
            score=d.get("score", 0),
            num_comments=d.get("num_comments", 0),
            permalink=d.get("permalink", ""),
            url=d.get("url", ""),
            selftext=d.get("selftext", ""),
        )

    def _parse_comment(self, d: dict) -> RedditComment:
        return RedditComment(
            author=d.get("author", "[deleted]"),
            body=d.get("body", ""),
            score=d.get("score", 0),
        )

    def _get(self, path: str, params: dict):
        try:
            res = self._client.get(path, params=params)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            raise RedditError(
                f"Reddit returned {e.response.status_code} for {path}"
            ) from e
        except httpx.HTTPError as e:
            raise RedditError(f"Could not reach Reddit for {path}") from e

    def close(self) -> None:
        self._client.close()
