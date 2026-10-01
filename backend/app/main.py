"""AccessPath backend entry point.

Run from the `backend/` directory:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AccessPath API",
    description="Backend API for the AccessPath software engineering project.",
    version="0.1.0",
)

# Allow the frontend dev server to call the API. Tighten this before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: once routers.py defines `router = APIRouter()`, register it here:
# from app.routers import router
# app.include_router(router)

# TODO: once database.py and models.py are set up, create tables on startup:
# from app.database import Base, engine
# Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "AccessPath API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
