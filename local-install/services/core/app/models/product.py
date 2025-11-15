from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    price = Column(Float, nullable=True)
    image_url = Column(Text, nullable=True)
    source = Column(String(64), nullable=True)  # 'ozon', 'wildberries', etc
    description = Column(Text, nullable=True)
    rating = Column(Float, nullable=True)
    linked_step_id = Column(Integer, ForeignKey("steps.id", ondelete="SET NULL"), nullable=True)
    created_from_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "url": self.url,
            "price": self.price,
            "image_url": self.image_url,
            "source": self.source,
            "description": self.description,
            "rating": self.rating,
            "linked_step_id": self.linked_step_id,
            "created_at": self.created_at.isoformat(),
        }


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    product = relationship("Product")

    def to_dict(self, include_product=True):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "added_at": self.added_at.isoformat(),
        }
        if include_product and self.product:
            data["product"] = self.product.to_dict()
        return data