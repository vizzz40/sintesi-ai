import httpx
import pytest
import respx

from app.services.reddit_client import RedditClient, RedditError

BASE = "https://www.reddit.com"


def make_client() -> RedditClient:
    return RedditClient(
        client=httpx.Client(base_url=BASE, headers={"User-Agent": "test"}, timeout=5.0)
    )


@respx.mock
def test_top_posts_parses_listing():
    payload = {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc",
                        "title": "Best ETL tools in 2026",
                        "author": "dataguy",
                        "score": 420,
                        "num_comments": 37,
                        "permalink": "/r/dataengineering/comments/abc/best_etl/",
                        "url": "https://reddit.com/r/dataengineering/comments/abc",
                        "selftext": "what are you all using?",
                    },
                },
                {"kind": "t3", "data": {"id": "def", "title": "Airflow vs Dagster"}},
            ]
        }
    }
    respx.get(f"{BASE}/r/dataengineering/top.json").mock(
        return_value=httpx.Response(200, json=payload)
    )

    posts = make_client().top_posts("dataengineering")

    assert len(posts) == 2
    assert posts[0].id == "abc"
    assert posts[0].score == 420
    assert posts[1].title == "Airflow vs Dagster"
    assert posts[1].author == "[deleted]"


@respx.mock
def test_top_comments_parses_second_listing():
    payload = [
        {"data": {"children": []}},
        {
            "data": {
                "children": [
                    {"kind": "t1", "data": {"author": "a", "body": "use dbt", "score": 90}},
                    {"kind": "t1", "data": {"author": "b", "body": "spark", "score": 12}},
                    {"kind": "more", "data": {"count": 5}},
                ]
            }
        },
    ]
    respx.get(f"{BASE}/r/dataengineering/comments/abc.json").mock(
        return_value=httpx.Response(200, json=payload)
    )

    comments = make_client().top_comments("dataengineering", "abc")

    assert len(comments) == 2
    assert comments[0].body == "use dbt"
    assert comments[1].author == "b"


@respx.mock
def test_top_comments_respects_limit():
    children = [
        {"kind": "t1", "data": {"author": str(i), "body": "x", "score": i}} for i in range(10)
    ]
    payload = [{"data": {"children": []}}, {"data": {"children": children}}]
    respx.get(f"{BASE}/r/sub/comments/p.json").mock(
        return_value=httpx.Response(200, json=payload)
    )

    comments = make_client().top_comments("sub", "p", limit=3)

    assert len(comments) == 3


@respx.mock
def test_rate_limit_raises_reddit_error():
    respx.get(f"{BASE}/r/sub/top.json").mock(return_value=httpx.Response(429))

    with pytest.raises(RedditError):
        make_client().top_posts("sub")


@respx.mock
def test_network_failure_raises_reddit_error():
    respx.get(f"{BASE}/r/sub/top.json").mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(RedditError):
        make_client().top_posts("sub")
