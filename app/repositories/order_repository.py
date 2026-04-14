from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order
from app.schemas import CreateOrderRequest


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: CreateOrderRequest) -> Order:
        order = Order(
            customer_id=payload.customer_id,
            item_sku=payload.item_sku,
            quantity=payload.quantity,
            amount=payload.amount,
            simulation=payload.simulation.model_dump(mode="json"),
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get(self, order_id: str) -> Order | None:
        return self.db.get(Order, order_id)

    def list(self) -> list[Order]:
        stmt = select(Order).order_by(Order.created_at.desc())
        return list(self.db.scalars(stmt))

    def save(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def increment_fulfillment_runs(self, order: Order) -> Order:
        order.fulfillment_runs += 1
        return self.save(order)
