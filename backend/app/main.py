"""
EVE Online Management Platform - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.security import get_rate_limiter
from app.api.v1 import auth, characters, killmails, map, routes, corporations, market, fleets


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
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(characters.router, prefix="/api/v1/characters", tags=["characters"])
app.include_router(killmails.router, prefix="/api/v1/killmails", tags=["killmails"])
app.include_router(map.router, prefix="/api/v1/map", tags=["map"])
app.include_router(routes.router, prefix="/api/v1/routes", tags=["routes"])
app.include_router(corporations.router, prefix="/api/v1/corporations", tags=["corporations"])
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(fleets.router, prefix="/api/v1/fleets", tags=["fleets"])


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

