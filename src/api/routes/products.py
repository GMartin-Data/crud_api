"""Product-related API routes.

This module implements the REST API endpoints for product management.
"""

import logging
from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.database.connection import get_session
from src.api.models.product import (
    Product,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "", 
    response_model=List[ProductRead],
    responses={200: {"description": "List of products retrieved successfully"}},
)
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
        
    Raises:
        HTTPException: 
            - 500: If an unexpected error occurs
    """
    products = session.exec(
        select(Product).order_by(Product.ProductID).offset(skip).limit(limit)
    ).all()
    return products


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    responses={
        200: {"description": "product retrieved successfully"},
        404: {
            "description": "product not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Product with ID 123 not found"}
                }
            }
        },
    }    
)
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
        HTTPException: 
            - 404: If product is not found
            - 500: If an unexpected error occurs
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    return product


@router.post(
    "/",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Product created successfully"},
        409: {
            "description": "Product number already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Product with number BK-NEW-001 already exists"
                    }
                }
            },
        },
    },
)
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
        
    Raises:
        HTTPException: 
            - 409: If product number or name already exists
            - 500: If an unexpected database constraint violation occurs

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

    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig)
        if "AK_Product_Name" in error_msg:
            logger.warning(
                "Attempted to create product with duplicate name: %s",
                product.Name,
                extra={
                    "product_name": product.Name,
                    "error_type": "duplicate_name",
                }
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with the name '{product.Name}' already exists."
            )
        elif "AK_Product_ProductNumber" in error_msg:
            logger.warning(
                "Attempted to create product with duplicate number: %s",
                product.ProductNumber,
                extra={
                    "product_number": product.ProductNumber,
                    "error_type": "duplicate_number",
                }
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with the product number '{product.ProductNumber}' already exists."
            )
        else:
            # Log unexpected integrity errors with full context
            logger.error(
                "Unexpected database constraint violation while creating product: %s",
                error_msg,
                extra={
                    "product_data": product.model_dump(),
                    "error_type": "unknown_constraint",
                    "error_details": error_msg,
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected database constraint violation occurred."
            )


@router.put(
    "/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Product updated successfully"},
        404: {
            "description": "Product not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Product with ID 123 not found"}
                }
            }
        },
        409: {
            "description": "Product update violates unique constraints",
            "content": {
                "application/json": {
                    "examples": {
                        "name_conflict": {
                            "summary": "Name already exists",
                            "value": {"detail": "A product with the name 'Mountain-200 Black, 38' already exists"}
                        },
                        "number_conflict": {
                            "summary": "Product number already exists",
                            "value": {"detail": "A product with the product number 'BK-MTB2-038' already exists"}
                        }
                    }
                }
            }
        }
    }
)
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
        HTTPException: 
            - 404 if product is not found
            - 409 if update violates unique constraints (name or product number)
            - 500 if an unexpected database error occurs
    """
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    try:
        # Update product fields
        product_data = product.model_dump(exclude_unset=True)
        for key, value in product_data.items():
            setattr(db_product, key, value)

        # Update ModifiedDate
        db_product.ModifiedDate = datetime.now(timezone.utc)

        session.add(db_product)
        session.commit()
        session.refresh(db_product)

        return db_product

    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig)
        
        if "AK_Product_Name" in error_msg:
            logger.warning(
                "Attempted to update product %s with duplicate name: %s",
                product_id,
                product.Name,
                extra={
                    "product_id": product_id,
                    "new_name": product.Name,
                    "error_type": "duplicate_name_update",
                }
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with the name '{product.Name}' already exists."
            )
        elif "AK_Product_ProductNumber" in error_msg:
            logger.warning(
                "Attempted to update product %s with duplicate number: %s",
                product_id,
                product.ProductNumber,
                extra={
                    "product_id": product_id,
                    "new_number": product.ProductNumber,
                    "error_type": "duplicate_number_update",
                }
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with the product number '{product.ProductNumber}' already exists."
            )
        else:
            # Log unexpected integrity errors with full context
            logger.error(
                "Unexpected constraint violation while updating product %s: %s",
                product_id,
                error_msg,
                extra={
                    "product_id": product_id,
                    "update_data": product.model_dump(exclude_unset=True),
                    "error_type": "unknown_constraint",
                    "error_details": error_msg,
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected database constraint violation occurred."
            )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Product successfully deleted"},
        404: {
            "description": "Product not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Product with ID 123 not found"}
                }
            }
        },
        409: {
            "description": "Product cannot be deleted due to existing references",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot delete product as it has associated sales orders"
                    }
                }
            }
        }
    }
)
async def delete_product(
    product_id: int,
    session: Session = Depends(get_session),
):
    """Delete a product.

    Args:
        product_id: ID of the product to delete
        session: Database session

    Raises:
        HTTPException: 
            - 404 if product is not found
            - 409 if product cannot be deleted due to existing references
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    try:
        session.delete(product)
        session.commit()
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig)
        if "FK_SalesOrderDetail_Product_ProductID" in error_msg:
            logger.warning(
                "Attempted to delete product with existing sales orders: %s",
                product_id,
                extra={
                    "product_id": product_id,
                    "error_type": "delete_constraint_violation",
                }
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete product as it has associated sales orders"
            )
        else:
            # Log unexpected integrity errors with full context
            logger.error(
                "Unexpected constraint violation while deleting product: %s",
                error_msg,
                extra={
                    "product_id": product_id,
                    "error_type": "unknown_constraint",
                    "error_details": error_msg,
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while deleting the product"
            )
