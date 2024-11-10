"""Shared test configuration.

The environment is set before any application module is imported, so `Settings` is never
constructed without a database URL.
"""

from __future__ import annotations

import os

os.environ.setdefault("CLEARED_ENVIRONMENT", "test")
os.environ.setdefault(
    "CLEARED_DATABASE_URL",
    "postgresql+asyncpg://cleared_app:cleared_app@127.0.0.1:5432/cleared_test",
)
os.environ.setdefault("CLEARED_SECRET_KEY", "test-only-secret-key-not-for-production")
