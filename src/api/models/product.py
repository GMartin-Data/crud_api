"""Product-related models for the API.

This module contains SQLModel models that correspond to the Product-related tables
in the SalesLT schema of the database.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from pydantic import validator
from sqlmodel import Field, Relationship, SQLModel


class ProductBase(SQLModel):
    """Base model for Product with shared attributes.
    
    This model contains fields that are common to both creation
    and database storage, excluding auto-generated fields.
    """
    Name: str = Field(nullable=False)
    ProductNumber: str = Field(nullable=False)
    Color: Optional[str] = None
    StandardCost: Decimal = Field(nullable=False)
    ListPrice: Decimal = Field(nullable=False)
    Size: Optional[str] = None
    Weight: Optional[Decimal] = None
    SellStartDate: datetime = Field(nullable=False)
    SellEndDate: Optional[datetime] = None
    DiscontinuedDate: Optional[datetime] = None
    ThumbNailPhoto: Optional[bytes] = None
    ThumbnailPhotoFileName: Optional[str] = None
    ProductModelID: Optional[int] = Field(default=None)
    ProductCategoryID: Optional[int] = Field(default=None)

    # Field validators
    @validator('Name')
    def validate_name(cls, v):
        if len(v) > 100:
            raise ValueError('Name must be 100 characters or less')
        return v

    @validator('ProductNumber')
    def validate_product_number(cls, v):
        if len(v) > 50:
            raise ValueError('ProductNumber must be 50 characters or less')
        return v

    @validator('Color')
    def validate_color(cls, v):
        if v is not None and len(v) > 30:
            raise ValueError('Color must be 30 characters or less')
        return v

    @validator('Size')
    def validate_size(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError('Size must be 10 characters or less')
        return v

    @validator('ThumbnailPhotoFileName')
    def validate_photo_filename(cls, v):
        if v is not None and len(v) > 100:
            raise ValueError('ThumbnailPhotoFileName must be 100 characters or less')
        return v

    @validator('Weight')
    def validate_weight(cls, v):
        if v is not None:
            # Ensure weight has at most 2 decimal places and is within valid range
            return Decimal(str(v)).quantize(Decimal('0.01'))
        return v


# Define the link model first so it can be referenced by other models
class ProductModelProductDescription(SQLModel, table=True):
    """Junction table between ProductModel and ProductDescription."""

    __tablename__ = "ProductModelProductDescription"
    __table_args__ = {"schema": "SalesLT"}

    ProductModelID: int = Field(
        foreign_key="SalesLT.ProductModel.ProductModelID", primary_key=True
    )
    ProductDescriptionID: int = Field(
        foreign_key="SalesLT.ProductDescription.ProductDescriptionID", primary_key=True
    )
    Culture: str = Field(primary_key=True)
    rowguid: str = Field(nullable=False)
    ModifiedDate: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )


class ProductDescription(SQLModel, table=True):
    """ProductDescription model representing the SalesLT.ProductDescription table."""

    __tablename__ = "ProductDescription"
    __table_args__ = {"schema": "SalesLT"}

    ProductDescriptionID: Optional[int] = Field(default=None, primary_key=True)
    Description: str = Field(nullable=False)
    rowguid: str = Field(nullable=False)
    ModifiedDate: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Define the relationship to ProductModel through the link table
    product_models: List["ProductModel"] = Relationship(
        back_populates="descriptions",
        link_model=ProductModelProductDescription
    )


class ProductModel(SQLModel, table=True):
    """ProductModel model representing the SalesLT.ProductModel table."""

    __tablename__ = "ProductModel"
    __table_args__ = {"schema": "SalesLT"}

    ProductModelID: Optional[int] = Field(default=None, primary_key=True)
    Name: str = Field(nullable=False)
    CatalogDescription: Optional[str] = None
    rowguid: str = Field(nullable=False)
    ModifiedDate: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    products: List["Product"] = Relationship(back_populates="product_model")
    descriptions: List[ProductDescription] = Relationship(
        back_populates="product_models",
        link_model=ProductModelProductDescription
    )


class ProductCategory(SQLModel, table=True):
    """ProductCategory model representing the SalesLT.ProductCategory table."""

    __tablename__ = "ProductCategory"
    __table_args__ = {"schema": "SalesLT"}

    ProductCategoryID: Optional[int] = Field(default=None, primary_key=True)
    ParentProductCategoryID: Optional[int] = Field(
        default=None, foreign_key="SalesLT.ProductCategory.ProductCategoryID"
    )
    Name: str = Field(nullable=False)
    rowguid: str = Field(nullable=False)
    ModifiedDate: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    products: List["Product"] = Relationship(back_populates="product_category")
    parent_category: Optional["ProductCategory"] = Relationship(
        back_populates="subcategories",
        sa_relationship_kwargs={"remote_side": "ProductCategory.ProductCategoryID"},
    )
    subcategories: List["ProductCategory"] = Relationship(back_populates="parent_category")


class Product(ProductBase, table=True):
    """Product model representing the SalesLT.Product table.
    
    This model extends ProductBase to include:
    1. Database-specific configurations (__tablename__, __table_args__)
    2. Auto-generated fields (ProductID, rowguid, ModifiedDate)
    3. Relationship configurations
    """
    __tablename__ = "Product"
    __table_args__ = {"schema": "SalesLT"}

    # Auto-generated fields
    ProductID: Optional[int] = Field(default=None, primary_key=True)
    rowguid: str = Field(nullable=False)
    ModifiedDate: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Foreign key fields (moved to ProductBase)
    ProductModelID: Optional[int] = Field(
        default=None, foreign_key="SalesLT.ProductModel.ProductModelID"
    )
    ProductCategoryID: Optional[int] = Field(
        default=None, foreign_key="SalesLT.ProductCategory.ProductCategoryID"
    )

    # Back references
    product_model: Optional[ProductModel] = Relationship(back_populates="products")
    product_category: Optional[ProductCategory] = Relationship(back_populates="products")


class ProductCreate(ProductBase):
    """Schema for creating a new product.
    
    Inherits from ProductBase to include all required fields for creation,
    while excluding auto-generated fields that will be set by the API.
    """
    pass


class ProductUpdate(SQLModel):
    """Schema for updating a product.
    
    All fields are optional to allow partial updates.
    """
    Name: Optional[str] = None
    ProductNumber: Optional[str] = None
    Color: Optional[str] = None
    StandardCost: Optional[Decimal] = None
    ListPrice: Optional[Decimal] = None
    Size: Optional[str] = None
    Weight: Optional[Decimal] = None
    SellStartDate: Optional[datetime] = None
    SellEndDate: Optional[datetime] = None
    DiscontinuedDate: Optional[datetime] = None
    ProductModelID: Optional[int] = None
    ProductCategoryID: Optional[int] = None


class ProductRead(SQLModel):
    """Schema for reading a product.
    
    Includes all fields that should be returned in API responses,
    excluding binary data (ThumbNailPhoto) to prevent serialization issues.
    """
    ProductID: int
    Name: str
    ProductNumber: str
    Color: Optional[str] = None
    StandardCost: Decimal
    ListPrice: Decimal
    Size: Optional[str] = None
    Weight: Optional[Decimal] = None
    SellStartDate: datetime
    SellEndDate: Optional[datetime] = None
    DiscontinuedDate: Optional[datetime] = None
    ThumbnailPhotoFileName: Optional[str] = None
    ProductModelID: Optional[int] = None
    ProductCategoryID: Optional[int] = None
    ModifiedDate: datetime
    rowguid: str

    class Config:
        """Pydantic model configuration."""
        from_attributes = True
