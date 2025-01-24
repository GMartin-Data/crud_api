"""Main application module.

This module sets up and configures the FastAPI application.
It includes all route modules and handles application-wide settings.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.products import router as products_router
from src.config.logger import setup_logger
from src.database.utils import (
    verify_database_connection,
    get_database_info,
    verify_required_tables,
)

# Set up application logger
logger = setup_logger("app.main", "app.log")

# Create FastAPI application
app = FastAPI(
    title="Product Management API",
    description="API for managing products in the AdventureWorks database",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products_router)


@app.on_event("startup")
async def startup_event():
    """Perform startup tasks.

    This function runs when the application starts.
    It verifies the database connection and logs the result.
    """
    logger.info("🚀 Starting up the application")

    # First verify database connection
    success, error = verify_database_connection()
    if not success:
        logger.error(f"❌ Failed to connect to the database: {error}")
        return

    logger.info("✅ Successfully connected to the database")

    # Get database information
    db_info = get_database_info()
    logger.info("Database Information:")
    for key, value in db_info.items():
        if key == "available_tables":
            logger.info("Available Tables:")
            for table in value:
                logger.info(f"  - {table}")
        else:
            logger.info(f"{key}: {value}")

    # Verify required tables exist
    success, error = verify_required_tables()
    if not success:
        logger.error(f"❌ Required tables missing: {error}")
        return

    logger.info("✅ All required tables verified")


@app.on_event("shutdown")
async def shutdown_event():
    """Perform shutdown tasks.

    This function runs when the application shuts down.
    It handles cleanup tasks and logs the shutdown.
    """
    logger.info("🛑 Shutting down the application")


@app.get("/")
async def root():
    """Root endpoint.

    Returns:
        dict: Basic API information
    """
    return {
        "message": "Welcome to the Product Management API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health check status and database connection status
    """
    db_success, db_error = verify_database_connection()
    return {
        "status": "healthy" if db_success else "unhealthy",
        "database": {
            "status": "connected" if db_success else "disconnected",
            "error": db_error,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info",
    )
