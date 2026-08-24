from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import Settings, get_settings
from app.services.sources.base import SourceComment, SourcePost


class SummarizerError(Exception):
    pass


class HotTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str


class Consensus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: str
    hot_topics: list[HotTopic]


SYSTEM_PROMPT = (
    "You read the top recent posts and comments about a topic and report the public consensus. "
    "Summarize what people are actually discussing and agreeing or disagreeing on. "
    "Be concise and neutral. Do not invent details that aren't in the posts. "
    'Reply with JSON: {"overview": str, "hot_topics": [{"title": str, "summary": str}]}. '
    "Give 3 to 5 hot topics."
)

MAX_SELFTEXT = 600
MAX_COMMENT = 280


class Summarizer:
    def __init__(
        self,
        settings: Settings | None = None,
        complete: Callable[[str], str] | None = None,
    ):
        self.settings = settings or get_settings()
        self._complete = complete or self._groq_complete

    def summarize(
        self,
        query: str,
        posts: list[SourcePost],
        comments: dict[str, list[SourceComment]] | None = None,
    ) -> Consensus:
        prompt = self._build_prompt(query, posts, comments or {})
        raw = self._complete(prompt)
        try:
            return Consensus.model_validate_json(raw)
        except ValidationError as e:
            raise SummarizerError("LLM returned unexpected output") from e

    def _build_prompt(
        self,
        query: str,
        posts: list[SourcePost],
        comments: dict[str, list[SourceComment]],
    ) -> str:
        lines = [f"Topic: {query}", "Top recent posts:", ""]
        for i, post in enumerate(posts, start=1):
            lines.append(f"{i}. {post.title} (score {post.score}, {post.num_comments} comments)")
            if post.selftext:
                lines.append(f"   body: {post.selftext[:MAX_SELFTEXT]}")
            for c in comments.get(post.id, []):
                lines.append(f"   - comment ({c.score}): {c.body[:MAX_COMMENT]}")
            lines.append("")
        return "\n".join(lines)

    def _groq_complete(self, prompt: str) -> str:
        from groq import Groq, GroqError

        if not self.settings.groq_api_key:
            raise SummarizerError("GROQ_API_KEY is not configured")

        client = Groq(api_key=self.settings.groq_api_key)
        try:
            res = client.chat.completions.create(
                model=self.settings.groq_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "consensus",
                        "strict": True,
                        "schema": Consensus.model_json_schema(),
                    },
                },
                temperature=0.3,
            )
        except GroqError as e:
            raise SummarizerError("Groq request failed") from e
        finally:
            client.close()
        return res.choices[0].message.content or ""
