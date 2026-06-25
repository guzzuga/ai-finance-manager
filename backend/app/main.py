"""AI Finance Manager — FastAPI application entry point."""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import APP_NAME, APP_VERSION, DEFAULT_CATEGORIES
from app.database.connection import init_db, SessionLocal
from app.models.category import Category

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _seed_default_categories(db) -> None:
    """Insert default categories if the table is empty."""
    existing = db.query(Category).count()
    if existing > 0:
        return

    logger.info("Seeding %d default categories...", len(DEFAULT_CATEGORIES))
    import uuid

    for cat_cfg in DEFAULT_CATEGORIES:
        kw = cat_cfg.get("keywords", [])
        cat = Category(
            id=str(uuid.uuid4()),
            name=cat_cfg["name"],
            type=cat_cfg["type"],
            icon=cat_cfg.get("icon", "📦"),
            keywords=json.dumps(kw) if kw else None,
            user_id=None,
        )
        db.add(cat)
    db.commit()
    logger.info("Default categories seeded.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting %s v%s...", APP_NAME, APP_VERSION)
    init_db()

    db = SessionLocal()
    try:
        _seed_default_categories(db)
        # Seed default marketplaces
        from app.services.konveksi_service import KonveksiService
        KonveksiService.seed_default_marketplaces(db)
    finally:
        db.close()

    yield

    logger.info("Shutting down %s...", APP_NAME)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="AI-powered personal finance manager with natural language input.",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.routers.auth import router as auth_router
from app.routers.transactions import router as transactions_router
from app.routers.konveksi import router as konveksi_router
app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(konveksi_router)

# Serve static files (dashboard)
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
    }


@app.get("/dashboard", tags=["dashboard"])
def serve_dashboard():
    """Serve the dashboard HTML."""
    return FileResponse(str(static_dir / "dashboard.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
