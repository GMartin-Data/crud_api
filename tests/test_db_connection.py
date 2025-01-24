"""Test suite for database connectivity.

These tests verify that:
1. We can connect to the database
2. Basic queries work
3. Our session management functions properly
4. We can inspect table structures
"""

import pytest
from sqlmodel import Session, text

from src.database.session import engine, get_session
from src.database.database_utils import (
    verify_database_connection,
    inspect_table_structure,
)


def test_database_connection():
    """Verify basic database connectivity."""
    success, error = verify_database_connection()
    assert success, f"Database connection failed: {error}"


def test_session_context_manager():
    """Verify session context manager works properly."""
    with Session(engine) as session:
        # Try a simple query
        result = session.exec(text("SELECT 1")).one()
        assert result == (1,), "Basic query failed"


def test_get_session():
    """Test the get_session dependency function."""
    # get_session is a generator, we need to use next() to get the session
    session = next(get_session())
    try:
        result = session.exec(text("SELECT 1")).one()
        assert result == (1,), "Session query failed"
    finally:
        session.close()


def test_product_table_structure():
    """Verify Product table structure can be inspected."""
    structure = inspect_table_structure("Product")
    assert "error" not in structure, "Failed to inspect Product table"

    # Verify essential columns exist with correct types
    assert "Name" in structure, "Product table missing Name column"
    assert structure["Name"]["data_type"] == "Name", "Unexpected type for Name column"
    assert not structure["Name"]["is_nullable"], "Name should not be nullable"

    assert "ProductNumber" in structure, "Product table missing ProductNumber column"
    assert not structure["ProductNumber"]["is_nullable"], (
        "ProductNumber should not be nullable"
    )


def test_invalid_table_name():
    """Test behavior with non-existent table."""
    structure = inspect_table_structure("NonExistentTable")
    assert "error" in structure, "Should report error for non-existent table"
    assert "Table not found: SalesLT.NonExistentTable" in structure["error"], (
        "Unexpected error message"
    )


@pytest.mark.parametrize("table_name", ["Product", "ProductCategory", "ProductModel"])
def test_related_tables_exist(table_name: str):
    """Verify existence of product-related tables."""
    structure = inspect_table_structure(table_name)
    assert "error" not in structure, f"Failed to inspect {table_name} table"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
