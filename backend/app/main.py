"""
EVE Online Management Platform - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.security import get_rate_limiter
from app.api.v1 import auth, characters, killmails, map, routes, corporations, market, fleets, mail, contacts, calendar, contracts, wallet, industry, blueprints, planetary, loyalty, fittings, skills, clones, bookmarks, structures, moons, sov


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="EVE Online Management Platform",
    description="A comprehensive EVE Online management platform with ESI integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Initialize rate limiter
get_rate_limiter(app)

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
# Note: Traefik strips /api/v1 prefix, so routers are mounted at /auth, /characters, etc.
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(characters.router, prefix="/characters", tags=["characters"])
app.include_router(killmails.router, prefix="/killmails", tags=["killmails"])
app.include_router(map.router, prefix="/map", tags=["map"])
app.include_router(routes.router, prefix="/routes", tags=["routes"])
app.include_router(corporations.router, prefix="/corporations", tags=["corporations"])
app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(fleets.router, prefix="/fleets", tags=["fleets"])
app.include_router(mail.router, prefix="/mail", tags=["mail"])
app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
app.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
app.include_router(industry.router, prefix="/industry", tags=["industry"])
app.include_router(blueprints.router, prefix="/blueprints", tags=["blueprints"])
app.include_router(planetary.router, prefix="/planetary", tags=["planetary"])
app.include_router(loyalty.router, prefix="/loyalty", tags=["loyalty"])
app.include_router(fittings.router, prefix="/fittings", tags=["fittings"])
app.include_router(skills.router, prefix="/skills", tags=["skills"])
app.include_router(clones.router, prefix="/clones", tags=["clones"])
app.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])
app.include_router(structures.router, prefix="/structures", tags=["structures"])
app.include_router(moons.router, prefix="/moons", tags=["moons"])
app.include_router(sov.router, prefix="/sov", tags=["sovereignty"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "EVE Online Management Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.core.database import engine
    from sqlalchemy import text
    
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status
    }

