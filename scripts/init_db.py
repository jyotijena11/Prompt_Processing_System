from app.core.database import Base, engine
from app.models import PromptJob, SemanticCacheEntry  # noqa: F401


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
