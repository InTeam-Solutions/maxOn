from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    price: Optional[float] = None
    image_url: Optional[HttpUrl] = None
    source: Optional[str] = None  # 'ozon', 'wildberries', etc
    description: Optional[str] = None
    rating: Optional[float] = None


class ProductCreate(ProductBase):
    user_id: str
    linked_step_id: Optional[int] = None
    created_from_prompt: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    user_id: str
    linked_step_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CartItemBase(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemCreate(CartItemBase):
    user_id: str


class CartItemResponse(CartItemBase):
    id: int
    user_id: str
    added_at: datetime
    product: Optional[ProductResponse] = None

    class Config:
        from_attributes = True