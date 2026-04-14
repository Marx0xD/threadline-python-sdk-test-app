from __future__ import annotations

from fastapi import FastAPI
import httpx

from app.core.config import get_settings
from app.schemas import (
    DownstreamResponse,
    InventoryReserveRequest,
    PaymentAuthorizeRequest,
    ShipmentCreateRequest,
    SimulationConfig,
)


class DownstreamHTTPClient:
    """
    Calls fake downstream services over HTTP so the demo still generates
    outbound client spans without needing multiple processes.
    """

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.base_url = get_settings().downstream_base_url

    async def reserve_inventory(
        self, order_id: str, item_sku: str, quantity: int, simulation: SimulationConfig
    ) -> DownstreamResponse:
        payload = InventoryReserveRequest(
            order_id=order_id,
            item_sku=item_sku,
            quantity=quantity,
            simulation=simulation,
        )
        return await self._post("/internal/inventory/reserve", payload)

    async def authorize_payment(
        self, order_id: str, customer_id: str, amount: float, simulation: SimulationConfig
    ) -> DownstreamResponse:
        payload = PaymentAuthorizeRequest(
            order_id=order_id,
            customer_id=customer_id,
            amount=amount,
            simulation=simulation,
        )
        return await self._post("/internal/payments/authorize", payload)

    async def create_shipment(
        self, order_id: str, item_sku: str, quantity: int, simulation: SimulationConfig
    ) -> DownstreamResponse:
        payload = ShipmentCreateRequest(
            order_id=order_id,
            item_sku=item_sku,
            quantity=quantity,
            simulation=simulation,
        )
        return await self._post("/internal/shipments/create", payload)

    async def _post(
        self,
        path: str,
        payload: InventoryReserveRequest | PaymentAuthorizeRequest | ShipmentCreateRequest,
    ) -> DownstreamResponse:
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url=self.base_url,
            timeout=30.0,
        ) as client:
            response = await client.post(path, json=payload.model_dump(mode="json"))
            response.raise_for_status()
            return DownstreamResponse.model_validate(response.json())
