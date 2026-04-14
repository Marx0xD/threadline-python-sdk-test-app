from __future__ import annotations

import asyncio

from fastapi import APIRouter

from app.schemas import (
    DownstreamResponse,
    InventoryReserveRequest,
    PaymentAuthorizeRequest,
    ShipmentCreateRequest,
)


router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/inventory/reserve", response_model=DownstreamResponse)
async def reserve_inventory(payload: InventoryReserveRequest) -> DownstreamResponse:
    if payload.simulation.slow_inventory_seconds:
        await asyncio.sleep(payload.simulation.slow_inventory_seconds)

    if payload.simulation.inventory_fail:
        return DownstreamResponse(
            ok=False,
            message="Inventory reservation failed for requested SKU",
        )

    return DownstreamResponse(ok=True, reference=f"inv-{payload.order_id[:8]}")


@router.post("/payments/authorize", response_model=DownstreamResponse)
async def authorize_payment(payload: PaymentAuthorizeRequest) -> DownstreamResponse:
    if payload.simulation.slow_payment_seconds:
        await asyncio.sleep(payload.simulation.slow_payment_seconds)

    if payload.simulation.payment_fail:
        return DownstreamResponse(
            ok=False,
            message="Payment authorization was declined",
        )

    return DownstreamResponse(ok=True, reference=f"pay-{payload.order_id[:8]}")


@router.post("/shipments/create", response_model=DownstreamResponse)
async def create_shipment(payload: ShipmentCreateRequest) -> DownstreamResponse:
    if payload.simulation.slow_shipment_seconds:
        await asyncio.sleep(payload.simulation.slow_shipment_seconds)

    if payload.simulation.shipment_fail:
        return DownstreamResponse(
            ok=False,
            message="Shipment creation failed downstream",
        )

    return DownstreamResponse(ok=True, reference=f"shp-{payload.order_id[:8]}")
