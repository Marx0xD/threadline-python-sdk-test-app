from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.clients import DownstreamHTTPClient
from app.repositories import OrderRepository
from app.schemas import (
    CreateOrderRequest,
    DownstreamResponse,
    InventoryStatus,
    ManualFulfillRequest,
    OrderStatus,
    PaymentStatus,
    SimulationConfig,
)
from app.services.fulfillment import run_fulfillment_job


class OrderService:
    def __init__(self, db: Session, app: FastAPI) -> None:
        self.repository = OrderRepository(db)
        self.downstream = DownstreamHTTPClient(app)
        self.app = app

    async def create_order(
        self,
        payload: CreateOrderRequest,
        background_tasks: BackgroundTasks,
    ):
        order = self.repository.create(payload)

        inventory_result = await self._reserve_inventory(order.id, payload)
        order = self._get_required_order(order.id)
        if not inventory_result.ok:
            return order

        payment_result = await self._authorize_payment(order.id, payload)
        order = self._get_required_order(order.id)
        if not payment_result.ok:
            return order

        self._transition(order, "status", OrderStatus.PROCESSING, reason="ready_for_fulfillment")
        order.last_error = None
        order = self.repository.save(order)

        if payload.simulation.missing_fulfillment:
            return order

        background_tasks.add_task(run_fulfillment_job, self.app, order.id)
        if payload.simulation.duplicate_fulfillment:
            background_tasks.add_task(run_fulfillment_job, self.app, order.id)
        return self._get_required_order(order.id)

    def get_order(self, order_id: str):
        order = self.repository.get(order_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} was not found",
            )
        return order

    def list_orders(self):
        return self.repository.list()

    def trigger_manual_fulfillment(
        self,
        order_id: str,
        payload: ManualFulfillRequest,
        background_tasks: BackgroundTasks,
    ):
        order = self.get_order(order_id)
        simulation = SimulationConfig.model_validate(order.simulation or {})
        if payload.simulation is not None:
            simulation = payload.simulation

        background_tasks.add_task(
            run_fulfillment_job,
            self.app,
            order.id,
            simulation.model_dump(mode="json"),
        )
        return order

    async def _reserve_inventory(self, order_id: str, payload: CreateOrderRequest):
        order = self._get_required_order(order_id)

        try:
            result = await self.downstream.reserve_inventory(
                order_id=order.id,
                item_sku=order.item_sku,
                quantity=order.quantity,
                simulation=payload.simulation,
            )
        except Exception as exc:
            self._transition(order, "inventory_status", InventoryStatus.FAILED, error=str(exc))
            self._transition(order, "status", OrderStatus.FAILED, reason="inventory_http_error")
            order.last_error = f"Inventory client error: {exc}"
            self.repository.save(order)
            return DownstreamResponse(ok=False, message=f"Inventory client error: {exc}")

        if result.ok:
            self._transition(
                order,
                "inventory_status",
                InventoryStatus.RESERVED,
                reference=result.reference,
            )
            order.last_error = None
            self.repository.save(order)
            return result

        self._transition(
            order,
            "inventory_status",
            InventoryStatus.FAILED,
            error=result.message,
        )
        self._transition(order, "status", OrderStatus.FAILED, reason="inventory_failed")
        order.last_error = result.message
        self.repository.save(order)
        return result

    async def _authorize_payment(self, order_id: str, payload: CreateOrderRequest):
        order = self._get_required_order(order_id)

        try:
            result = await self.downstream.authorize_payment(
                order_id=order.id,
                customer_id=order.customer_id,
                amount=order.amount,
                simulation=payload.simulation,
            )
        except Exception as exc:
            self._transition(order, "payment_status", PaymentStatus.FAILED, error=str(exc))
            self._transition(order, "status", OrderStatus.FAILED, reason="payment_http_error")
            order.last_error = f"Payment client error: {exc}"
            self.repository.save(order)
            return DownstreamResponse(ok=False, message=f"Payment client error: {exc}")

        if result.ok:
            self._transition(
                order,
                "payment_status",
                PaymentStatus.AUTHORIZED,
                reference=result.reference,
            )
            order.last_error = None
            self.repository.save(order)
            return result

        self._transition(order, "payment_status", PaymentStatus.FAILED, error=result.message)
        self._transition(order, "status", OrderStatus.FAILED, reason="payment_failed")
        order.last_error = result.message
        self.repository.save(order)
        return result

    def _get_required_order(self, order_id: str):
        order = self.repository.get(order_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} was not found",
            )
        return order

    def _transition(self, order, field: str, new_value: str, **metadata: object) -> None:
        if getattr(order, field) == new_value:
            return

        setattr(order, field, new_value)
