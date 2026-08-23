import json

import pytest

from app.config import Settings
from app.services.reddit_client import RedditComment, RedditPost
from app.services.summarizer import Consensus, Summarizer, SummarizerError


def make_post(pid="abc", title="Best ETL tools", selftext="what are you using?"):
    return RedditPost(
        id=pid,
        title=title,
        author="dataguy",
        score=420,
        num_comments=37,
        permalink="/r/dataengineering/comments/abc/",
        url="https://reddit.com/abc",
        selftext=selftext,
    )


def test_summarize_returns_validated_consensus():
    canned = json.dumps(
        {
            "overview": "People mostly recommend dbt.",
            "hot_topics": [{"title": "dbt", "summary": "Widely recommended."}],
        }
    )
    summarizer = Summarizer(complete=lambda _: canned)

    result = summarizer.summarize("dataengineering", [make_post()])

    assert isinstance(result, Consensus)
    assert result.overview == "People mostly recommend dbt."
    assert result.hot_topics[0].title == "dbt"


def test_invalid_llm_output_raises():
    summarizer = Summarizer(complete=lambda _: '{"overview": "missing topics"}')

    with pytest.raises(SummarizerError):
        summarizer.summarize("sub", [make_post()])


def test_extra_llm_fields_raise():
    summarizer = Summarizer(
        complete=lambda _: '{"overview": "ok", "hot_topics": [], "extra": true}'
    )

    with pytest.raises(SummarizerError):
        summarizer.summarize("sub", [make_post()])


def test_missing_api_key_raises():
    settings = Settings(_env_file=None, groq_api_key="")
    summarizer = Summarizer(settings=settings)

    with pytest.raises(SummarizerError, match="GROQ_API_KEY"):
        summarizer._groq_complete("prompt")


def test_prompt_includes_posts_and_comments():
    captured = {}

    def fake_complete(prompt):
        captured["prompt"] = prompt
        return json.dumps({"overview": "ok", "hot_topics": []})

    summarizer = Summarizer(complete=fake_complete)
    comments = {"abc": [RedditComment(author="a", body="use dbt", score=90)]}

    summarizer.summarize("data engineering", [make_post()], comments)

    prompt = captured["prompt"]
    assert "data engineering" in prompt
    assert "Best ETL tools" in prompt
    assert "use dbt" in prompt


def test_long_text_is_truncated():
    captured = {}

    def fake_complete(prompt):
        captured["prompt"] = prompt
        return json.dumps({"overview": "ok", "hot_topics": []})

    long_body = "x" * 5000
    summarizer = Summarizer(complete=fake_complete)

    summarizer.summarize("sub", [make_post(selftext=long_body)])

    assert "x" * 5000 not in captured["prompt"]
