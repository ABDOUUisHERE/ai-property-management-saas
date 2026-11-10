"""Run with uvicorn app.main:create_app --factory; no configuration at import."""

from app.bootstrap import create_app

__all__ = ["create_app"]
