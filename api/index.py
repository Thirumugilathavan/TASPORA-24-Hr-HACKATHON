"""Vercel Serverless Function entrypoint for NALAM FastAPI backend.

This entrypoint ensures the application root is properly placed in the Python path
and exports the FastAPI ASGI `app` instance for Vercel's Python runtime.
"""
import os
import sys

# Ensure repository root is on sys.path
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from app.main import app

__all__ = ["app"]
