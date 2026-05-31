from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Topic

TOPICS = [
    ("data-engineering", "Data Engineering", "data engineering"),
    ("devops", "DevOps", "devops"),
    ("machine-learning", "Machine Learning", "machine learning"),
    ("python", "Python", "python"),
    ("webdev", "Web Development", "web development"),
    ("startups", "Startups", "startups"),
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        for slug, display_name, query in TOPICS:
            exists = session.exec(select(Topic).where(Topic.slug == slug)).first()
            if exists is None:
                session.add(Topic(slug=slug, display_name=display_name, query=query))
        session.commit()


if __name__ == "__main__":
    seed()
    print("seeded topics")
