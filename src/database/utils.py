"""Database utility functions.

This module provides tools for:
1. Database connectivity verification
2. Table structure inspection
3. Database information gathering
4. Schema validation
"""

from typing import Dict, Optional, Tuple

from sqlmodel import Session, text

from src.config.logger import setup_logger
from .connection import get_engine

# Create a logger specifically for database utilities
utils_logger = setup_logger("database.utils", "database_utils.log")


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
        with Session(get_engine()) as session:
            version = session.exec(text("SELECT @@VERSION")).one()
            utils_logger.info(
                f"✅ Database connection successful\nSQL Server version: {version}"
            )
            return True, None

    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        utils_logger.error(f"❌ {error_msg}")
        return False, error_msg


def verify_required_tables() -> Tuple[bool, Optional[str]]:
    """Verify that all required tables exist in the database.

    This function checks for the existence of all product-related tables
    in the SalesLT schema.

    Returns:
        Tuple[bool, Optional[str]]: Success status and error message if any

    Raises:
        ValueError: If required tables are missing
    """
    try:
        required_tables = {
            "Product",
            "ProductCategory",
            "ProductModel",
            "ProductDescription",
            "ProductModelProductDescription",
        }

        with Session(get_engine()) as session:
            # Create a dynamic query with table names
            table_conditions = " OR ".join(
                f"t.name = '{table}'" for table in required_tables
            )
            table_query = text(f"""
                SELECT t.name AS table_name
                FROM sys.tables t
                JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE s.name = 'SalesLT'
                AND ({table_conditions})
            """)

            results = session.execute(table_query).fetchall()
            existing_tables = {row.table_name for row in results}
            missing_tables = required_tables - existing_tables

            if missing_tables:
                error_msg = f"Missing required tables: {missing_tables}"
                utils_logger.error(f"❌ {error_msg}")
                return False, error_msg

            utils_logger.info("✅ All required tables exist")
            return True, None

    except Exception as e:
        error_msg = f"Failed to verify tables: {str(e)}"
        utils_logger.error(f"❌ {error_msg}")
        return False, error_msg


def get_database_info() -> Dict[str, str]:
    """Retrieve basic information about the database connection.

    This function collects various pieces of information about the
    database connection, which can be useful for documentation and
    troubleshooting purposes.

    Returns:
        dict: Database information including:
            - server_version: SQL Server version
            - database_name: Current database name
            - available_tables: List of tables in the database
    """
    info: Dict[str, str] = {}

    try:
        with Session(get_engine()) as session:
            # Get SQL server version
            version = session.exec(text("SELECT @@VERSION")).one()
            info["server_version"] = version

            # Get database name
            db_name = session.exec(text("SELECT DB_NAME()")).one()
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

            utils_logger.info("✅ Successfully retrieved database information")

    except Exception as e:
        error_msg = f"❌ Failed to retrieve database information: {str(e)}"
        utils_logger.error(error_msg)
        info["error"] = error_msg

    return info


def inspect_table_structure(table_name: str, schema: str = "SalesLT") -> Dict:
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
    table_info: Dict = {}
    try:
        with Session(get_engine()) as session:
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

            utils_logger.info(
                f"✅ Successfully retrieved structure for {schema}.{table_name}"
            )

    except Exception as e:
        error_msg = f"Failed to retrieve table structure: {str(e)}"
        utils_logger.error(f"❌ {error_msg}")
        table_info["error"] = error_msg

    return table_info
