import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import EcommerceDatabaseService
from .models import (
    Cart,
    CartItem,
    Customer,
    CustomerCreate,
    CustomerUpdate,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Product,
    ProductCreate,
    ProductUpdate,
    ShippingAddress,
    UserRole,
)

def _sample_products() -> List[Product]:
    return [
        Product(
            id=str(uuid.uuid4()),
            title="Sample Acrylic Paint Set",
            price=29.99,
            rating=4.5,
            review_count=120,
            image="/placeholder-paint.jpg",
            category="paints",
            stock_quantity=50,
            description="Starter set for demos.",
            is_featured=True,
        ),
        Product(
            id=str(uuid.uuid4()),
            title="Premium Roller Kit",
            price=45.0,
            rating=4.8,
            review_count=42,
            image="/placeholder-roller.jpg",
            category="tools",
            stock_quantity=25,
            description="Rollers and trays.",
            is_featured=True,
        ),
        Product(
            id=str(uuid.uuid4()),
            title="Interior Primer 1gal",
            price=38.5,
            rating=4.2,
            review_count=88,
            image="/placeholder-primer.jpg",
            category="primers",
            stock_quantity=100,
            description="Low-VOC primer.",
            is_featured=False,
        ),
    ]


class EcommerceMemoryService(EcommerceDatabaseService):
    def __init__(self) -> None:
        self._products: Dict[str, Product] = {}
        self._customers: Dict[str, Customer] = {}
        self._carts: Dict[str, Cart] = {}
        self._orders: Dict[str, Order] = {}
        for p in _sample_products():
            self._products[p.id] = p

    async def get_products(
        self, search_params: Optional[Dict[str, Any]] = None
    ) -> List[Product]:
        items = list(self._products.values())
        if not search_params:
            return sorted(items, key=lambda x: x.title.lower())
        category = search_params.get("category")
        min_price = search_params.get("min_price")
        max_price = search_params.get("max_price")
        min_rating = search_params.get("min_rating")
        in_stock_only = search_params.get("in_stock_only")
        query = (search_params.get("query") or "").strip().lower()
        sort_by = search_params.get("sort_by") or "name"
        sort_order = search_params.get("sort_order") or "asc"

        if category:
            items = [p for p in items if p.category == category]
        if min_price is not None:
            items = [p for p in items if p.price >= min_price]
        if max_price is not None:
            items = [p for p in items if p.price <= max_price]
        if min_rating is not None:
            items = [p for p in items if p.rating >= min_rating]
        if in_stock_only:
            items = [p for p in items if p.in_stock and p.stock_quantity > 0]
        if query:
            items = [
                p
                for p in items
                if query in p.title.lower()
                or (p.description and query in p.description.lower())
            ]

        reverse = sort_order == "desc"
        if sort_by == "price":
            items.sort(key=lambda x: x.price, reverse=reverse)
        elif sort_by == "rating":
            items.sort(key=lambda x: x.rating, reverse=reverse)
        else:
            items.sort(key=lambda x: x.title.lower(), reverse=reverse)
        return items

    async def get_product(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)

    async def create_product(self, product: ProductCreate) -> Product:
        pid = str(uuid.uuid4())
        row = Product(
            id=pid,
            title=product.title,
            price=product.price,
            original_price=product.original_price,
            rating=product.rating,
            review_count=product.review_count,
            image=product.image,
            category=product.category,
            in_stock=product.in_stock,
            stock_quantity=product.stock_quantity,
            description=product.description,
            tags=product.tags or [],
            specifications=product.specifications or {},
            is_featured=product.is_featured,
        )
        self._products[pid] = row
        return row

    async def update_product(
        self, product_id: str, product: ProductUpdate
    ) -> Optional[Product]:
        existing = self._products.get(product_id)
        if not existing:
            return None
        data = existing.model_dump()
        for k, v in product.model_dump(exclude_unset=True).items():
            if v is not None:
                data[k] = v
        updated = Product(**data)
        self._products[product_id] = updated
        return updated

    async def delete_product(self, product_id: str) -> bool:
        if product_id not in self._products:
            return False
        del self._products[product_id]
        return True

    async def get_product_categories(self) -> List[str]:
        cats = {p.category for p in self._products.values()}
        return sorted(cats)

    async def get_featured_products(self, limit: int = 10) -> List[Product]:
        featured = [p for p in self._products.values() if p.is_featured]
        featured.sort(key=lambda x: x.rating, reverse=True)
        return featured[:limit]

    async def get_related_products(
        self, product_id: str, limit: int = 5
    ) -> List[Product]:
        base = self._products.get(product_id)
        if not base:
            return []
        same = [
            p
            for p in self._products.values()
            if p.category == base.category and p.id != product_id
        ]
        same.sort(key=lambda x: x.rating, reverse=True)
        return same[:limit]

    async def restore_product_stock(self, product_id: str, quantity: int) -> bool:
        p = self._products.get(product_id)
        if not p:
            return False
        p.stock_quantity += quantity
        p.in_stock = p.stock_quantity > 0
        return True

    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self._customers.get(customer_id)

    async def create_customer(self, customer: CustomerCreate) -> Customer:
        cid = str(uuid.uuid4())
        row = Customer(
            id=cid,
            email=customer.email,
            name=customer.name,
            phone=customer.phone,
            role=UserRole.CUSTOMER,
        )
        self._customers[cid] = row
        return row

    async def update_customer(
        self, customer_id: str, customer: CustomerUpdate
    ) -> Optional[Customer]:
        existing = self._customers.get(customer_id)
        if not existing:
            return None
        data = existing.model_dump()
        for k, v in customer.model_dump(exclude_unset=True).items():
            if v is not None:
                data[k] = v
        updated = Customer(**data)
        self._customers[customer_id] = updated
        return updated

    async def get_customer_by_email(self, email: str) -> Optional[Customer]:
        email_l = email.lower()
        for c in self._customers.values():
            if c.email.lower() == email_l:
                return c
        return None

    async def get_or_create_customer(
        self, user_id: str, email: str, name: str
    ) -> Customer:
        existing = self._customers.get(user_id)
        if existing:
            return existing
        row = Customer(
            id=user_id,
            email=email or f"{user_id}@local.dev",
            name=name or "Customer",
            role=UserRole.CUSTOMER,
            last_login=datetime.utcnow(),
        )
        self._customers[user_id] = row
        return row

    async def get_cart(self, user_id: str) -> Optional[Cart]:
        return self._carts.get(user_id)

    async def update_cart(self, user_id: str, cart: Cart) -> Cart:
        cart.id = user_id
        cart.user_id = user_id
        self._carts[user_id] = cart
        return cart

    async def clear_cart(self, user_id: str) -> bool:
        if user_id in self._carts:
            del self._carts[user_id]
        return True

    async def create_order(
        self,
        user_id: str,
        cart: Cart,
        shipping_address: Dict[str, Any],
        payment_method: str,
    ) -> Order:
        addr = ShippingAddress(**shipping_address)
        try:
            pm = PaymentMethod(payment_method)
        except ValueError:
            pm = PaymentMethod.CREDIT_CARD

        order_items: List[OrderItem] = []
        for ci in cart.items:
            prod = self._products.get(ci.product_id)
            unit = prod.price if prod else ci.product_price
            order_items.append(
                OrderItem(
                    product_id=ci.product_id,
                    product_title=ci.product_title,
                    quantity=ci.quantity,
                    unit_price=unit,
                    total_price=unit * ci.quantity,
                )
            )
            if prod:
                prod.stock_quantity -= ci.quantity
                prod.in_stock = prod.stock_quantity > 0

        subtotal = sum(i.total_price for i in order_items)
        tax = round(subtotal * 0.08, 2)
        shipping_cost = 9.99 if subtotal < 50 else 0.0
        total = round(subtotal + tax + shipping_cost, 2)
        oid = str(uuid.uuid4())
        order = Order(
            id=oid,
            customer_id=user_id,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            status=OrderStatus.PENDING,
            items=order_items,
            subtotal=subtotal,
            tax=tax,
            shipping_cost=shipping_cost,
            total=total,
            shipping_address=addr,
            payment_method=pm,
        )
        self._orders[oid] = order
        return order

    async def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    async def get_customer_orders(
        self,
        customer_id: str,
        status: Optional[OrderStatus] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> List[Order]:
        rows = [o for o in self._orders.values() if o.customer_id == customer_id]
        if status is not None:
            rows = [o for o in rows if o.status == status]
        rows.sort(key=lambda x: x.created_at, reverse=True)
        start = (page - 1) * page_size
        return rows[start : start + page_size]

    async def update_order_status(
        self, order_id: str, status: OrderStatus
    ) -> Optional[Order]:
        o = self._orders.get(order_id)
        if not o:
            return None
        o.status = status
        o.updated_at = datetime.utcnow()
        self._orders[order_id] = o
        return o

