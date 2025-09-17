import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from mvp.config import DATABASE_URL

# Общая Base доступна без инициализации (её безопасно импортировать в models.py)
Base = declarative_base()

class Database:
    """Обёртка для подключения к PostgreSQL через SQLAlchemy."""
    def __init__(self, url: str = None, echo: bool | None = None):
        self.url = url or DATABASE_URL
        if not self.url:
            raise RuntimeError("DATABASE_URL не задан в .env")

        self.echo = (os.getenv("DB_ECHO", "false").lower() == "true") if echo is None else bool(echo)
        self.engine = create_engine(self.url, echo=self.echo, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def get_session(self):
        return self.SessionLocal()

    def session_ctx(self):
        return _SessionCtx(self.SessionLocal)

class _SessionCtx:
    def __init__(self, SessionLocal):
        self._SessionLocal = SessionLocal
    def __enter__(self):
        self.session = self._SessionLocal()
        return self.session
    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        finally:
            self.session.close()

# ---- ленивый синглтон ----
_db: Database | None = None

def init_db(url: str | None = None, echo: bool | None = None) -> Database:
    """Вызывается один раз при старте (в app.py после load_dotenv)."""
    global _db
    _db = Database(url=url, echo=echo)
    return _db

def get_db() -> Database:
    """Возвращает инициализированный экземпляр. Если нет — кидает понятную ошибку."""
    if _db is None:
        raise RuntimeError("Database не инициализирован. Сначала вызови init_db() в app.py после load_dotenv.")
    return _db
