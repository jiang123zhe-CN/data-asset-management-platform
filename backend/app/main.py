from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api import auth, directories, fields, mappings, reviews, logs, users, reports, standards, tagging, datasources, compliance

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(directories.router)
app.include_router(fields.router)
app.include_router(mappings.router)
app.include_router(reviews.router)
app.include_router(logs.router)
app.include_router(users.router)
app.include_router(reports.router)
app.include_router(standards.router)
app.include_router(tagging.router)
app.include_router(datasources.router)
app.include_router(compliance.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
