from pydantic import BaseModel, Field

from app.schemas.order import SimulationConfig


class InventoryReserveRequest(BaseModel):
    order_id: str
    item_sku: str
    quantity: int = Field(gt=0)
    simulation: SimulationConfig


class PaymentAuthorizeRequest(BaseModel):
    order_id: str
    customer_id: str
    amount: float = Field(gt=0)
    simulation: SimulationConfig


class ShipmentCreateRequest(BaseModel):
    order_id: str
    item_sku: str
    quantity: int = Field(gt=0)
    simulation: SimulationConfig


class DownstreamResponse(BaseModel):
    ok: bool
    reference: str | None = None
    message: str | None = None
