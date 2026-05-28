from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=120)
    status: str = Field(default="active", min_length=1, max_length=32)


class UserPatch(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = Field(default=None, min_length=1, max_length=32)


class OrderCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    status: str = Field(default="pending", min_length=1, max_length=32)
    total_amount: float = Field(default=0, ge=0)
    note: str | None = None


class OrderPatch(BaseModel):
    user_id: str | None = Field(default=None, min_length=1, max_length=36)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    total_amount: float | None = Field(default=None, ge=0)
    note: str | None = None


class OrderItemCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=1000)
    unit_price: float = Field(ge=0)


class OrderItemPatch(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    quantity: int | None = Field(default=None, gt=0, le=1000)
    unit_price: float | None = Field(default=None, ge=0)


class AuditLogCreate(BaseModel):
    action: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1)
    user_id: str | None = Field(default=None, max_length=36)
    order_id: str | None = Field(default=None, max_length=36)


class ChaoticOrderCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(min_length=1, max_length=36)
    status: str = Field(default="pending", min_length=1, max_length=32)
    note: str | None = None
    items: list[OrderItemCreate] = Field(default_factory=list)
    fail_after_items: bool = Field(default=False, alias="failAfterItems")
