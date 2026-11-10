from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings

settings = get_settings()
url = settings.database_url
# Render commonly supplies postgres://; SQLAlchemy expects postgresql://.
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg://", 1)
elif url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(url, pool_pre_ping=True, pool_recycle=300, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
