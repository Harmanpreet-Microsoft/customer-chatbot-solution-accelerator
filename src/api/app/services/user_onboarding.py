import logging
from datetime import datetime, timedelta
import random
from typing import List
from ..models import Transaction, TransactionItem, OrderStatus
from ..cosmos_service import get_cosmos_service

logger = logging.getLogger(__name__)

SAMPLE_PRODUCTS = [
    {"id": "prod-001", "title": "Dusty Rose Paint - 1 Gallon", "price": 45.99},
    {"id": "prod-002", "title": "Forest Green Paint - 1 Gallon", "price": 42.99},
    {"id": "prod-003", "title": "Ocean Blue Paint - 1 Gallon", "price": 44.99},
    {"id": "prod-004", "title": "Sunset Orange Paint - 1 Gallon", "price": 43.99},
    {"id": "prod-005", "title": "Premium Paint Brush Set", "price": 29.99},
    {"id": "prod-006", "title": "Paint Roller Kit", "price": 19.99},
    {"id": "prod-007", "title": "Painter's Tape - 3 Pack", "price": 12.99},
    {"id": "prod-008", "title": "Drop Cloth Set", "price": 24.99},
]

async def create_demo_order_history(user_id: str) -> List[Transaction]:
    cosmos_service = get_cosmos_service()
    
    existing_orders = await cosmos_service.get_orders_by_customer(user_id, limit=1)
    if existing_orders:
        logger.info(f"User {user_id} already has order history, skipping demo creation")
        return []
    
    logger.info(f"Creating demo order history for new user: {user_id}")
    
    demo_orders = []
    now = datetime.utcnow()
    
    order_scenarios = [
        {
            "days_ago": 15,
            "status": OrderStatus.DELIVERED,
            "products": [
                {"id": "prod-001", "title": "Dusty Rose Paint - 1 Gallon", "price": 45.99, "qty": 2},
                {"id": "prod-005", "title": "Premium Paint Brush Set", "price": 29.99, "qty": 1},
            ]
        },
        {
            "days_ago": 45,
            "status": OrderStatus.DELIVERED,
            "products": [
                {"id": "prod-002", "title": "Forest Green Paint - 1 Gallon", "price": 42.99, "qty": 3},
                {"id": "prod-006", "title": "Paint Roller Kit", "price": 19.99, "qty": 1},
                {"id": "prod-007", "title": "Painter's Tape - 3 Pack", "price": 12.99, "qty": 2},
            ]
        },
        {
            "days_ago": 90,
            "status": OrderStatus.DELIVERED,
            "products": [
                {"id": "prod-003", "title": "Ocean Blue Paint - 1 Gallon", "price": 44.99, "qty": 1},
                {"id": "prod-008", "title": "Drop Cloth Set", "price": 24.99, "qty": 1},
            ]
        },
        {
            "days_ago": 150,
            "status": OrderStatus.DELIVERED,
            "products": [
                {"id": "prod-004", "title": "Sunset Orange Paint - 1 Gallon", "price": 43.99, "qty": 4},
                {"id": "prod-005", "title": "Premium Paint Brush Set", "price": 29.99, "qty": 2},
                {"id": "prod-006", "title": "Paint Roller Kit", "price": 19.99, "qty": 2},
            ]
        },
        {
            "days_ago": 200,
            "status": OrderStatus.DELIVERED,
            "products": [
                {"id": "prod-001", "title": "Dusty Rose Paint - 1 Gallon", "price": 45.99, "qty": 1},
                {"id": "prod-007", "title": "Painter's Tape - 3 Pack", "price": 12.99, "qty": 1},
            ]
        }
    ]
    
    for idx, scenario in enumerate(order_scenarios, start=1):
        order_date = now - timedelta(days=scenario["days_ago"])
        
        items = []
        subtotal = 0.0
        
        for prod in scenario["products"]:
            item_total = prod["price"] * prod["qty"]
            items.append(TransactionItem(
                product_id=prod["id"],
                product_title=prod["title"],
                quantity=prod["qty"],
                unit_price=prod["price"],
                total_price=item_total
            ))
            subtotal += item_total
        
        tax = round(subtotal * 0.08, 2)
        shipping = 0.0 if subtotal > 50 else 9.99
        total = subtotal + tax + shipping
        
        order_number = f"ORD-{user_id[:8].upper()}-{idx:04d}"
        
        transaction = Transaction(
            id=f"order-{user_id}-{idx}",
            user_id=user_id,
            order_number=order_number,
            status=scenario["status"],
            items=items,
            subtotal=subtotal,
            tax=tax,
            shipping=shipping,
            total=total,
            shipping_address={
                "street": "123 Demo Street",
                "city": "Seattle",
                "state": "WA",
                "zip": "98101",
                "country": "USA"
            },
            payment_method="Credit Card",
            payment_reference=f"PAY-{random.randint(100000, 999999)}",
            created_at=order_date,
            updated_at=order_date
        )
        
        try:
            transaction_dict = transaction.model_dump()
            transaction_dict["created_at"] = order_date.isoformat()
            transaction_dict["updated_at"] = order_date.isoformat()
            
            cosmos_service.transactions_container.create_item(transaction_dict)
            demo_orders.append(transaction)
            logger.info(f"Created demo order {order_number} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to create demo order: {e}")
    
    logger.info(f"Successfully created {len(demo_orders)} demo orders for user {user_id}")
    return demo_orders

