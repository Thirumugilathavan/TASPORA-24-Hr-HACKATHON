"""
Database table migration script for Health Camp & Follow-up Discovery tables.
Creates health_camp_sources, health_camps, and user_camp_preferences.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from app.core.config import settings
from app.models.base import Base
# Import all models to ensure metadata is populated
from app.models import *

def migrate():
    # settings.DATABASE_URL is sqlite+aiosqlite:///./carebridge.db
    # For sync table creation, use sqlite:///./carebridge.db
    db_url = settings.DATABASE_URL.replace("+aiosqlite", "")
    print(f"Connecting to database: {db_url}")
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(engine)
    print("Health Camp tables created successfully!")

if __name__ == "__main__":
    migrate()
