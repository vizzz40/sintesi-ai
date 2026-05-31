import httpx
import pytest
import respx

from app.services.sources.base import SourceError
from app.services.sources.hackernews import HackerNewsSource

BASE = "https://hn.algolia.com"


def make_source() -> HackerNewsSource:
    return HackerNewsSource(client=httpx.Client(base_url=BASE, timeout=5.0))


@respx.mock
def test_top_posts_parses_hits():
    payload = {
        "hits": [
            {
                "objectID": "111",
                "title": "Show HN: a tiny data tool",
                "author": "alice",
                "points": 240,
                "num_comments": 58,
                "url": "https://example.com/tool",
                "story_text": "",
            },
            {
                "objectID": "222",
                "title": "Ask HN: best ETL stack?",
                "author": "bob",
                "points": 90,
                "num_comments": 30,
                "url": None,
                "story_text": "<p>What are you all using?</p>",
            },
        ]
    }
    respx.get(f"{BASE}/api/v1/search").mock(return_value=httpx.Response(200, json=payload))

    posts = make_source().top_posts("data engineering")

    assert len(posts) == 2
    assert posts[0].id == "111"
    assert posts[0].score == 240
    assert posts[1].permalink == "https://news.ycombinator.com/item?id=222"
    assert posts[1].url == "https://news.ycombinator.com/item?id=222"
    assert posts[1].selftext == "What are you all using?"


@respx.mock
def test_top_comments_strips_html_and_skips_deleted():
    payload = {
        "children": [
            {"author": "carol", "text": "use <i>dbt</i> &amp; airflow", "points": 40},
            {"author": None, "text": None, "points": 0},
            {"author": "dave", "text": "<p>spark</p>", "points": 5},
        ]
    }
    respx.get(f"{BASE}/api/v1/items/111").mock(return_value=httpx.Response(200, json=payload))

    comments = make_source().top_comments("data engineering", "111")

    assert len(comments) == 2
    assert comments[0].body == "use dbt & airflow"
    assert comments[1].author == "dave"


@respx.mock
def test_top_comments_respects_limit():
    children = [{"author": str(i), "text": "x", "points": i} for i in range(10)]
    respx.get(f"{BASE}/api/v1/items/p").mock(
        return_value=httpx.Response(200, json={"children": children})
    )

    comments = make_source().top_comments("q", "p", limit=3)

    assert len(comments) == 3


@respx.mock
def test_http_error_raises_source_error():
    respx.get(f"{BASE}/api/v1/search").mock(return_value=httpx.Response(503))

    with pytest.raises(SourceError):
        make_source().top_posts("q")
