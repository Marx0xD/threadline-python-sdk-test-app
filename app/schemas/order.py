from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    FULFILLED = "fulfilled"
    FAILED = "failed"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    FAILED = "failed"


class InventoryStatus(StrEnum):
    PENDING = "pending"
    RESERVED = "reserved"
    FAILED = "failed"


class ShipmentStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    SHIPPED = "shipped"
    FAILED = "failed"


class SimulationConfig(BaseModel):
    # These toggles intentionally create broken workflow paths for investigation demos.
    inventory_fail: bool = False
    payment_fail: bool = False
    missing_fulfillment: bool = False
    duplicate_fulfillment: bool = False
    swallow_fulfillment_exception: bool = False
    shipment_fail: bool = False
    slow_inventory_seconds: float = Field(default=0, ge=0, le=30)
    slow_payment_seconds: float = Field(default=0, ge=0, le=30)
    slow_shipment_seconds: float = Field(default=0, ge=0, le=30)


class CreateOrderRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    item_sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=100)
    amount: float = Field(gt=0)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)


class ManualFulfillRequest(BaseModel):
    simulation: SimulationConfig | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    item_sku: str
    quantity: int
    amount: float
    status: OrderStatus
    payment_status: PaymentStatus
    inventory_status: InventoryStatus
    shipment_status: ShipmentStatus
    simulation: SimulationConfig
    fulfillment_runs: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class ResetResponse(BaseModel):
    message: str
