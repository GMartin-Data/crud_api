"""Test suite for database connectivity and utilities.

This module provides comprehensive testing for:
1. Database connection management
2. Session handling and lifecycle
3. Database information retrieval
4. Table structure inspection
"""

import pytest
from sqlmodel import Session, text

from src.database.connection import get_engine, get_session
from src.database.utils import (
    verify_database_connection,
    get_database_info,
    inspect_table_structure,
    verify_required_tables,
)


@pytest.fixture
def db_session():
    """Provide a database session for testing."""
    with Session(get_engine()) as session:
        yield session


class TestDatabaseConnection:
    """Test cases for database connection functionality."""

    def test_get_engine_singleton(self):
        """Verify that get_engine returns the same engine instance."""
        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1 is engine2, "Engine should be a singleton"

    def test_verify_connection(self):
        """Test database connection verification."""
        success, error = verify_database_connection()
        assert success, f"Database connection should succeed, got error: {error}"
        assert error is None, "No error should be present on successful connection"

    def test_session_context_manager(self, db_session):
        """Verify session context manager works properly."""
        result = db_session.exec(text("SELECT 1")).one()
        assert result == (1,), "Basic query should return 1"

    def test_session_generator(self):
        """Test the get_session dependency function."""
        session = next(get_session())
        try:
            result = session.exec(text("SELECT 1")).one()
            assert result == (1,), "Session query should return 1"
        finally:
            session.close()


class TestDatabaseInfo:
    """Test cases for database information retrieval."""

    def test_get_database_info(self):
        """Test retrieval of database information."""
        info = get_database_info()

        # Check required keys
        assert "server_version" in info, "Server version should be present"
        assert "database_name" in info, "Database name should be present"
        assert "available_tables" in info, "Available tables should be listed"

        # Verify we have tables
        assert isinstance(info["available_tables"], list), "Tables should be in a list"
        assert len(info["available_tables"]) > 0, "Should have at least one table"

    def test_required_tables_exist(self):
        """Verify that all required product-related tables exist."""
        success, error = verify_required_tables()
        assert success, f"Required tables should exist: {error}"


class TestTableInspection:
    """Test cases for table structure inspection."""

    def test_product_table_structure(self):
        """Verify Product table structure can be inspected."""
        structure = inspect_table_structure("Product")
        assert "error" not in structure, "Failed to inspect Product table"

        # Verify essential columns exist with correct types
        assert "Name" in structure, "Product table missing Name column"
        assert structure["Name"]["data_type"] == "Name", (
            "Unexpected type for Name column"
        )
        assert not structure["Name"]["is_nullable"], "Name should not be nullable"

        assert "ProductNumber" in structure, (
            "Product table missing ProductNumber column"
        )
        assert not structure["ProductNumber"]["is_nullable"], (
            "ProductNumber should not be nullable"
        )

    def test_product_table_constraints(self):
        """Verify Product table constraints."""
        structure = inspect_table_structure("Product")

        # Check primary key
        assert "ProductID" in structure, "Product table missing ProductID column"
        assert structure["ProductID"]["is_primary_key"], (
            "ProductID should be primary key"
        )

        # Check foreign keys (they should be nullable)
        assert "ProductModelID" in structure, "Missing ProductModelID column"
        assert structure["ProductModelID"]["is_nullable"], (
            "ProductModelID should be nullable"
        )

        assert "ProductCategoryID" in structure, "Missing ProductCategoryID column"
        assert structure["ProductCategoryID"]["is_nullable"], (
            "ProductCategoryID should be nullable"
        )

    def test_invalid_table_name(self):
        """Test behavior with non-existent table."""
        structure = inspect_table_structure("NonExistentTable")
        assert "error" in structure, "Should report error for non-existent table"
        assert "Table not found: SalesLT.NonExistentTable" in structure["error"], (
            "Unexpected error message"
        )

    @pytest.mark.parametrize(
        "table_name",
        [
            "Product",
            "ProductCategory",
            "ProductModel",
            "ProductDescription",
            "ProductModelProductDescription",
        ],
    )
    def test_table_structure(self, table_name: str):
        """Verify structure of all product-related tables."""
        structure = inspect_table_structure(table_name)
        assert "error" not in structure, f"Failed to inspect {table_name} table"

        # Common columns all tables should have
        assert "rowguid" in structure, f"{table_name} missing rowguid column"
        assert "ModifiedDate" in structure, f"{table_name} missing ModifiedDate column"

        # Verify ModifiedDate properties
        modified_date = structure["ModifiedDate"]
        assert modified_date["data_type"] == "datetime", (
            f"ModifiedDate in {table_name} should be datetime"
        )
        assert not modified_date["is_nullable"], (
            f"ModifiedDate in {table_name} should not be nullable"
        )


class TestDatabaseSetup:
    """Test cases for database setup and table verification."""

    def test_verify_required_tables(self):
        """Test that all required tables exist."""
        success, error = verify_required_tables()
        assert success, f"Required tables should exist: {error}"

    def test_table_relationships(self, db_session):
        """Verify that table relationships are properly set up."""
        # Check foreign key relationship between Product and ProductModel
        fk_query = text("""
            SELECT 
                OBJECT_NAME(f.parent_object_id) AS TableName,
                COL_NAME(fc.parent_object_id, fc.parent_column_id) AS ColumnName,
                OBJECT_NAME(f.referenced_object_id) AS ReferenceTableName,
                COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS ReferenceColumnName
            FROM sys.foreign_keys AS f
            INNER JOIN sys.foreign_key_columns AS fc
                ON f.object_id = fc.constraint_object_id
            WHERE OBJECT_NAME(f.parent_object_id) = 'Product'
                AND OBJECT_SCHEMA_NAME(f.parent_object_id) = 'SalesLT'
        """)

        results = db_session.execute(fk_query).fetchall()
        foreign_keys = {
            (row.ColumnName, row.ReferenceTableName, row.ReferenceColumnName)
            for row in results
        }

        expected_fks = {
            ("ProductModelID", "ProductModel", "ProductModelID"),
            ("ProductCategoryID", "ProductCategory", "ProductCategoryID"),
        }

        assert foreign_keys == expected_fks, (
            "Product table foreign keys don't match expected"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
