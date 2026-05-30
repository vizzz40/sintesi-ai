from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Topic

TOPICS = [
    ("data-engineering", "Data Engineering", "dataengineering"),
    ("devops", "DevOps", "devops"),
    ("polimi", "Politecnico di Milano", "Polimi"),
    ("machine-learning", "Machine Learning", "MachineLearning"),
    ("python", "Python", "Python"),
    ("webdev", "Web Development", "webdev"),
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        for slug, display_name, subreddit in TOPICS:
            exists = session.exec(select(Topic).where(Topic.slug == slug)).first()
            if exists is None:
                session.add(Topic(slug=slug, display_name=display_name, subreddit=subreddit))
        session.commit()


if __name__ == "__main__":
    seed()
    print("seeded topics")
