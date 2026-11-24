"""Compatibility ASGI entrypoint: the canonical `main:app` is already guarded.

Do not layer a second guard or accidentally serve the raw FastAPI application.
"""
from main import app
