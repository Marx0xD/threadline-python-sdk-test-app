from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from threadline.integrations.db.sqlalchemy import instrument_sqlalchemy

from app.core.config import get_settings


LabBase = declarative_base()

settings = get_settings()

threadline_db_url = settings.threadline_db
if threadline_db_url.startswith("postgresql://"):
    threadline_db_url = threadline_db_url.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args: dict[str, object] = {}
if threadline_db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

lab_engine = create_engine(threadline_db_url, connect_args=connect_args)
threadline_sqlalchemy = instrument_sqlalchemy(lab_engine)

ThreadlineLabSessionLocal = sessionmaker(
    bind=lab_engine,
    autoflush=False,
    autocommit=False,
    class_=Session,
)


def get_threadline_lab_db() -> Generator[Session, None, None]:
    db = ThreadlineLabSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_threadline_lab_db() -> None:
    from app.models import threadline_db_lab  # noqa: F401

    LabBase.metadata.create_all(bind=lab_engine)
