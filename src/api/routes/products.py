"""Product-related API routes.

This module implements the REST API endpoints for product management.
"""

from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timezone

from src.database.connection import get_session
from src.api.models.product import (
    Product,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=List[ProductRead])
async def list_products(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
):
    """List all products with pagination.

    Args:
        session: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of products
    """
    products = session.exec(
        select(Product).order_by(Product.ProductID).offset(skip).limit(limit)
    ).all()
    return products


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    session: Session = Depends(get_session),
):
    """Get a specific product by ID.

    Args:
        product_id: ID of the product to retrieve
        session: Database session

    Returns:
        Product details

    Raises:
        HTTPException: If product is not found
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    return product


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    session: Session = Depends(get_session),
):
    """Create a new product.

    Args:
        product: Product data from the request
        session: Database session

    Returns:
        Created product with auto-generated fields

    Note:
        Auto-generated fields (ProductID, rowguid, ModifiedDate) are set here
        before committing to the database.
    """
    try:
        # Convert ProductCreate to dict and add auto-generated fields
        product_data = product.model_dump()
        product_data.update(
            {"rowguid": str(uuid4()), "ModifiedDate": datetime.now(timezone.utc)}
        )

        # Create Product instance with all fields
        db_product = Product.model_validate(product_data)

        # Add and commit to database
        session.add(db_product)
        session.commit()
        session.refresh(db_product)

        return db_product

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log the error here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the product:\n{str(e)}"
        )


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    session: Session = Depends(get_session),
):
    """Update a product.

    Args:
        product_id: ID of the product to update
        product: Updated product data
        session: Database session

    Returns:
        Updated product

    Raises:
        HTTPException: If product is not found
    """
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    # Update product fields
    product_data = product.model_dump(exclude_unset=True)
    for key, value in product_data.items():
        setattr(db_product, key, value)

    session.add(db_product)
    session.commit()
    session.refresh(db_product)

    return db_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    session: Session = Depends(get_session),
):
    """Delete a product.

    Args:
        product_id: ID of the product to delete
        session: Database session

    Raises:
        HTTPException: If product is not found
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    session.delete(product)
    session.commit()
