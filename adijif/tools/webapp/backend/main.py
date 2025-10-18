"""FastAPI backend for PyADI-JIF Tools Explorer."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adijif.tools.webapp.backend.api import clock_router, converter_router, system_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting PyADI-JIF Tools Explorer API")
    yield
    logger.info("Shutting down PyADI-JIF Tools Explorer API")


# Create FastAPI app
app = FastAPI(
    title="PyADI-JIF Tools Explorer API",
    description="API for configuring JESD204 converters, clocks, and systems",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(converter_router, prefix="/api/converters", tags=["converters"])
app.include_router(clock_router, prefix="/api/clocks", tags=["clocks"])
app.include_router(system_router, prefix="/api/systems", tags=["systems"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "PyADI-JIF Tools Explorer API"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
