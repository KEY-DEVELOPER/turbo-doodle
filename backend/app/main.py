"""FastAPI application factory. Run with: uvicorn app.main:app --reload"""

from fastapi import FastAPI

from app import __version__
from app.api import health
from app.api.v1 import router as v1_router
from app.core.errors import ErrorResponse, install_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="EdgeLedger API",
        version=__version__,
        responses={"default": {"model": ErrorResponse, "description": "Error"}},
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(v1_router)
    return app


app = create_app()
