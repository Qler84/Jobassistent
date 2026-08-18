"""FastAPI-Einstiegspunkt."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import applications, auth, dashboard, jobs, profile, settings as settings_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kein Alembic fuer die MVP-Phase: Tabellen werden beim Start angelegt,
    # falls sie noch nicht existieren (idempotent, aendert keine bestehenden
    # Tabellen). Schema-Aenderungen nach dem ersten Deploy brauchen eine
    # echte Migration - siehe README.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Job-Assistent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(settings_router.router)
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
