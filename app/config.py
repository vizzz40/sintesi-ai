from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hn_base_url: str = "https://hn.algolia.com"
    hn_days: int = 7

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    database_url: str = "sqlite:///./sintesi.db"

    posts_per_digest: int = 15
    comments_per_post: int = 8

    # Public demos should normally disable arbitrary searches so visitors cannot
    # consume the owner's LLM quota. Curated topic digests remain available.
    allow_freeform_search: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
