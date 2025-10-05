from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.product import Product, CartItem


def create_product(
    session: Session,
    user_id: str,
    title: str,
    url: str,
    price: Optional[float] = None,
    image_url: Optional[str] = None,
    source: Optional[str] = None,
    description: Optional[str] = None,
    rating: Optional[float] = None,
    linked_step_id: Optional[int] = None,
    created_from_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new product"""
    product = Product(
        user_id=user_id,
        title=title.strip(),
        url=url,
        price=price,
        image_url=image_url,
        source=source,
        description=description,
        rating=rating,
        linked_step_id=linked_step_id,
        created_from_prompt=created_from_prompt
    )
    session.add(product)
    session.flush()
    return product.to_dict()


def get_product(session: Session, product_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a product by ID"""
    product = session.query(Product).filter(
        Product.id == product_id,
        Product.user_id == user_id
    ).first()
    return product.to_dict() if product else None


def list_products(
    session: Session,
    user_id: str,
    linked_step_id: Optional[int] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """List user's products"""
    q = session.query(Product).filter(Product.user_id == user_id)

    if linked_step_id:
        q = q.filter(Product.linked_step_id == linked_step_id)

    q = q.order_by(Product.created_at.desc()).limit(limit)

    return [product.to_dict() for product in q.all()]


def add_to_cart(
    session: Session,
    user_id: str,
    product_id: int,
    quantity: int = 1
) -> Optional[Dict[str, Any]]:
    """Add a product to cart"""
    # Verify product exists and belongs to user
    product = session.query(Product).filter(
        Product.id == product_id,
        Product.user_id == user_id
    ).first()

    if not product:
        return None

    # Check if already in cart
    cart_item = session.query(CartItem).filter(
        CartItem.user_id == user_id,
        CartItem.product_id == product_id
    ).first()

    if cart_item:
        # Update quantity
        cart_item.quantity += quantity
    else:
        # Create new cart item
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        session.add(cart_item)

    session.flush()
    return cart_item.to_dict()


def get_cart(session: Session, user_id: str) -> List[Dict[str, Any]]:
    """Get user's cart items"""
    cart_items = session.query(CartItem).filter(
        CartItem.user_id == user_id
    ).order_by(CartItem.added_at.desc()).all()

    return [item.to_dict() for item in cart_items]


def remove_from_cart(session: Session, cart_item_id: int, user_id: str) -> bool:
    """Remove an item from cart"""
    cart_item = session.query(CartItem).filter(
        CartItem.id == cart_item_id,
        CartItem.user_id == user_id
    ).first()

    if not cart_item:
        return False

    session.delete(cart_item)
    session.flush()
    return True


def clear_cart(session: Session, user_id: str) -> int:
    """Clear all items from user's cart"""
    count = session.query(CartItem).filter(CartItem.user_id == user_id).delete()
    session.flush()
    return count