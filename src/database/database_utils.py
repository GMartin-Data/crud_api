"""Database utility functions for connection testing and diagnostics.

This module provides tools for verifying database connectivity and gathering
system information using SQLModel's session management. It serves both as a
diagnostic tool and as an example of proper session usage.
"""

from typing import Optional, Tuple

from sqlmodel import Session, text

from .session import engine
from src.config.logger import setup_logger


# Create a logger specifically for connection testing
db_utils_logger = setup_logger("database_utils", "database_utils.log")


def verify_database_connection() -> Tuple[bool, Optional[str]]:
    """Test database connectivity using SQLModel session management.

    This function attempts to:
    1. Create a database session
    2. Execute a simple query to verify database access
    3. Retrieve basic database information

    Returns:
        Tuple[bool, Optional[str]]: a tuple containing:
            - Success status (True if connection works, False otherwise)
            - Error message if connection fails, None if successful
    """
    try:
        # Create a session with the new engine (from SQLAlchemy)
        with Session(engine) as session:
            # Execute a simple query to test connectivity
            # text() is SQLAlchemy's way of sending raw SQL safely
            # Notice that we don't need a `cursor` anymore
            version = session.scalars(text("SELECT @@VERSION")).one()

            db_utils_logger.info(
                f"✅ Database connection succesful\nSQL Server version: {version}"
            )
            return True, None

    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        db_utils_logger.error(f"❌ {error_msg}")
        return False, error_msg


def get_database_info() -> dict:
    """Retrieve basic information about the database connection.

    This function collects various pieces of information about the
    database connection, which can be useful for documentation and
    troubleshooting purposes.

    Returns:
        dict: Database information including:
            - driver version,
            - server version...
            And other relevant details.
    """
    info = {}

    try:
        with Session(engine) as session:
            # Get SQL server version
            version = session.scalars(text("SELECT @@VERSION")).one()
            info["server_version"] = version

            # Get database name
            db_name = session.scalars(text("SELECT DB_NAME()")).one()
            info["database_name"] = db_name

            # List all available tables and their schemas
            schema_query = text("""
                SELECT
                    s.name AS schema_name,
                    t.name AS table_name
                  FROM sys.tables t
                  JOIN sys.schemas s ON t.schema_id = s.schema_id
                 ORDER BY s.name, t.name                    
            """)

            schema_info = session.exec(schema_query).fetchall()
            info["available_tables"] = [f"{row[0]}.{row[1]}" for row in schema_info]

            db_utils_logger.info("✅ Successfully retrieved database information")

    except Exception as e:
        error_msg = f"❌ Failed to retrieve database information: {str(e)}"
        db_utils_logger.error(error_msg)
        info["error"] = error_msg

    return info


def inspect_table_structure(table_name: str, schema: str = "SalesLT") -> dict:
    """Examine the structure of a specific database table.

    This function retrieves detailed information about table columns,
    including their names, types, and constraints. This helps ensure
    our SQLModel definitions match the actual database structure.

    Args:
        table_name: Name of the table to inspect
        schema: Database schema name (defaults to SalesLT)

    Returns:
        dict: Column information including types and constraints
    """
    table_info = {}
    try:
        with Session(engine) as session:
            # Query to get column information
            columns_query = text("""
                SELECT 
                    c.name AS column_name,
                    t.name AS data_type,
                    c.max_length,
                    c.precision,
                    c.scale,
                    c.is_nullable,
                    CASE 
                        WHEN pk.column_id IS NOT NULL THEN 1 ELSE 0
                    END AS is_primary_key
                FROM sys.columns c
                JOIN sys.types t ON c.user_type_id = t.user_type_id
                JOIN sys.tables tbl ON c.object_id = tbl.object_id
                JOIN sys.schemas s ON tbl.schema_id = s.schema_id
                LEFT JOIN (
                    SELECT i.object_id, ic.column_id
                    FROM sys.index_columns ic
                    JOIN sys.indexes i ON ic.object_id = i.object_id 
                        AND ic.index_id = i.index_id
                    WHERE i.is_primary_key = 1
                ) pk ON c.object_id = pk.object_id 
                    AND c.column_id = pk.column_id
                WHERE tbl.name = :table_name
                AND s.name = :schema
                ORDER BY c.column_id
            """)

            result = session.execute(
                columns_query, {"table_name": table_name, "schema": schema}
            ).fetchall()

            if not result:
                raise ValueError(f"Table not found: {schema}.{table_name}")

            # Organize column information
            for row in result:
                column_info = {
                    "data_type": row.data_type,
                    "max_length": row.max_length,
                    "precision": row.precision,
                    "scale": row.scale,
                    "is_nullable": row.is_nullable,
                    "is_primary_key": row.is_primary_key,
                }
                table_info[row.column_name] = column_info

            db_utils_logger.info(
                f"✅ Successfully retrieved structure for {schema}.{table_name}"
            )

    except Exception as e:
        error_msg = f"Failed to retrieve table structure: {str(e)}"
        db_utils_logger.error(f"❌ {error_msg}")
        table_info["error"] = error_msg

    return table_info


if __name__ == "__main__":
    print("⏳ Testing database connection...")
    success, error = verify_database_connection()

    if success:
        print("\n✅ Connection successful!")
        print("\nRetrieving database information...")
        info = get_database_info()

        print("\n⛁ Database Information:")
        for key, value in info.items():
            if key == "available_tables":
                print("\nAvailable Tables:")
                for table in value:
                    print(f"  - {table}")
            else:
                print(f"{key}: {value}")

        # Add table structure inspection
        table_name: str = input("Enter the table name to inspect: ")
        print(f"\n🔎 Inspecting '{table_name}' table structure:")
        table_structure = inspect_table_structure(table_name)
        for column, details in table_structure.items():
            print(f"\n{column}:")
            for attr, value in details.items():
                print(f"  {attr}: {value}")
    else:
        print(f"\n❌ Connection failed:\nError: {error}")
