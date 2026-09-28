"""Versioned REST API (PRD 14.6). Each module adds its own router file here and includes it."""

from fastapi import APIRouter

router = APIRouter(prefix="/v1")
