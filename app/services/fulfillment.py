from __future__ import annotations

from fastapi import FastAPI

from app.clients import DownstreamHTTPClient
from app.db.session import SessionLocal
from app.repositories import OrderRepository
from app.schemas import OrderStatus, ShipmentStatus, SimulationConfig


def _transition(order, field: str, new_value: str, **metadata: object) -> None:
    if getattr(order, field) == new_value:
        return

    setattr(order, field, new_value)


async def run_fulfillment_job(
    app: FastAPI,
    order_id: str,
    simulation_override: dict | None = None,
) -> None:
    with SessionLocal() as db:
        repository = OrderRepository(db)
        order = repository.get(order_id)

        if order is None:
            return

        simulation = SimulationConfig.model_validate(
            simulation_override or order.simulation or {}
        )

        order = repository.increment_fulfillment_runs(order)

        if order.status != OrderStatus.PROCESSING:
            return

        _transition(order, "shipment_status", ShipmentStatus.QUEUED)
        repository.save(order)

        if simulation.swallow_fulfillment_exception:
            try:
                raise RuntimeError("Simulated fulfillment worker exception")
            except Exception as exc:
                # This is intentionally swallowed to create a silent logical failure.
                return

        downstream = DownstreamHTTPClient(app)

        try:
            shipment_result = await downstream.create_shipment(
                order_id=order.id,
                item_sku=order.item_sku,
                quantity=order.quantity,
                simulation=simulation,
            )
        except Exception as exc:
            _transition(order, "shipment_status", ShipmentStatus.FAILED, error=str(exc))
            _transition(order, "status", OrderStatus.FAILED, reason="shipment_http_error")
            order.last_error = f"Shipment client error: {exc}"
            repository.save(order)
            return

        if not shipment_result.ok:
            _transition(
                order,
                "shipment_status",
                ShipmentStatus.FAILED,
                error=shipment_result.message,
            )
            _transition(order, "status", OrderStatus.FAILED, reason="shipment_failed")
            order.last_error = shipment_result.message
            repository.save(order)
            return

        _transition(
            order,
            "shipment_status",
            ShipmentStatus.SHIPPED,
            reference=shipment_result.reference,
        )
        _transition(order, "status", OrderStatus.FULFILLED, reason="shipment_created")
        order.last_error = None
        repository.save(order)
