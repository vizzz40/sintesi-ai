from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Which backend feeds the digests: "hackernews" or "reddit".
    content_source: str = "hackernews"

    hn_base_url: str = "https://hn.algolia.com"
    hn_days: int = 7

    # Reddit's public JSON needs no OAuth, only a unique User-Agent. Kept as a
    # selectable source, but it 403s datacenter IPs so it only works locally.
    reddit_user_agent: str = "sintesi/0.1 (personal portfolio project)"
    reddit_base_url: str = "https://www.reddit.com"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    database_url: str = "sqlite:///./sintesi.db"

    posts_per_digest: int = 15
    comments_per_post: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
