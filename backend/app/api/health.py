"""Liveness probe. Unversioned so infrastructure checks never break across API versions."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: Literal["ok"]
    version: str


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", version=__version__)
