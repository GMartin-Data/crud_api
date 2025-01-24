"""Database session management for SQLModel.

This module handles the setup and management of database sessions using SQLModel.
It provides the necessary components for connecting to our SQL Server database
and managing database sessions throughout our application's lifecycle.
"""

import os
from typing import Generator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlmodel import Session, create_engine
from src.config.logger import setup_logger

# Source and set environment variables
load_dotenv()
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")

# set up logging
db_logger = setup_logger("database.session", "database_session.log")

# Explicitely specify the driver and encode it properly
driver = os.getenv("SQL_DRIVER").replace(" ", "+")  # "ODBC+Driver+18+for+SQL+Server"

# Create connection parameters with proper URL encoding
params = {
    "TrustServerCertificate": "yes",
    "Encrypt": "yes",
    "Connection+Timeout": "60",
}
params_str = "&".join(
    f"{key}={quote_plus(str(value))}" for key, value in params.items()
)

# Create the database URL for SQL Server
# We will transform our existing connection parameters into a SQLAlchemy URL
DATABASE_URL = (
    f"mssql+pyodbc://{SQL_USERNAME}:{SQL_PASSWORD}"
    f"@{SQL_SERVER}/{SQL_DATABASE}"
    f"?driver={driver}&{params_str}"
)

# Log the connection string without sensitive info
safe_url = DATABASE_URL.replace(SQL_PASSWORD, "***")
db_logger.debug("Connecting with URL: %s", safe_url)

# Create engine with specific ODBC configuration
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # Verify connection before using from pool
    pool_recycle=3_600,  # Recycle connection after 1 hour
    connect_args={"timeout": 60},
)


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for dependency injection.

    This function creates a new database session for each request and ensures
    proper cleanup when the request is complete.
    It's designed to be used with FastAPI's dependency injection system.

    Yields:
        Session: A SQLModel session for database operations

    Example:
        @app.get('/items')
        def read_items(session: Session = Depends(get_session)):
            return session.query(Item).all()
    """
    with Session(engine) as session:
        try:
            db_logger.debug("📖 Creating new database session")
            yield session
        except Exception as e:
            db_logger.error(f"❌ Database session error: {str(e)}")
            raise
        finally:
            db_logger.debug("📕 Closing database session")


# Test engine configuration at module load
try:
    with engine.connect() as connection:
        db_logger.info("✅ Database engine configured successfully")
except Exception as e:
    db_logger.error(f"❌ Database engine configuration failed: {str(e)}")
