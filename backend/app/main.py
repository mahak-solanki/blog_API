from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 - registers models with SQLAlchemy metadata
from app.core.config import settings
from app.db.session import Base, engine
from app.routers.auth import router as auth_router
from app.routers.posts import router as posts_router

# For this small interview task, create tables automatically at startup.
# For a larger production app, use Alembic migrations instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(posts_router)


@app.get("/health/")
def health_check():
    """Liveness endpoint required by the task."""
    return {"status": "ok"}


@app.get("/readiness/")
def readiness_check():
    """Readiness endpoint required by the task; verifies database connectivity."""
    from sqlalchemy import text
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}
