"""Database connection and session management.

This module handles:
1. Database connection configuration and URL generation
2. SQLAlchemy engine singleton management
3. Database session creation and lifecycle
4. Connection pooling and timeout settings
"""

import os
from typing import Generator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlmodel import Session, create_engine
from src.config.logger import setup_logger

# Set up logging
connection_logger = setup_logger("database.connection", "database_connection.log")

# Load environment variables
load_dotenv()

# Database connection parameters
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")

# Connection parameters
CONN_PARAMS = {
    "TrustServerCertificate": "yes",
    "Encrypt": "yes",
    "Connection+Timeout": "60",
}


def create_database_url() -> str:
    """Create the database URL from environment variables."""
    driver = SQL_DRIVER.replace(" ", "+")
    params_str = "&".join(
        f"{key}={quote_plus(str(value))}" for key, value in CONN_PARAMS.items()
    )

    url = (
        f"mssql+pyodbc://{SQL_USERNAME}:{SQL_PASSWORD}"
        f"@{SQL_SERVER}/{SQL_DATABASE}"
        f"?driver={driver}&{params_str}"
    )

    # Log URL without sensitive information
    safe_url = url.replace(SQL_PASSWORD, "***")
    connection_logger.debug("Database URL: %s", safe_url)

    return url


# Global engine instance
_engine = None


def get_engine():
    """Get the SQLAlchemy engine, creating it if necessary.

    Returns:
        SQLAlchemy engine instance
    """
    global _engine
    if _engine is None:
        connection_logger.debug("Creating new database engine")
        _engine = create_engine(
            create_database_url(),
            echo=False,
            pool_pre_ping=True,  # Verify connection before using from pool
            pool_recycle=3_600,  # Recycle connection after 1 hour
            connect_args={"timeout": 60},
        )
    return _engine


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
    with Session(get_engine()) as session:
        try:
            connection_logger.debug("📖 Creating new database session")
            yield session
        except Exception as e:
            connection_logger.error(f"❌ Database session error: {str(e)}")
            raise
        finally:
            connection_logger.debug("📕 Closing database session")
