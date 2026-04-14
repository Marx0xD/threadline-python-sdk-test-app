from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db, reset_db
from app.schemas import (
    CreateOrderRequest,
    ManualFulfillRequest,
    OrderRead,
    ResetResponse,
)
from app.services import OrderService


router = APIRouter(tags=["orders"])
test_router = APIRouter(prefix="/test", tags=["test"])


@router.post("/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: CreateOrderRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderRead:
    service = OrderService(db, request.app)
    order = await service.create_order(payload, background_tasks)
    return OrderRead.model_validate(order)


@router.get("/orders/{order_id}", response_model=OrderRead)
def get_order(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderRead:
    service = OrderService(db, request.app)
    return OrderRead.model_validate(service.get_order(order_id))


@router.get("/orders", response_model=list[OrderRead])
def list_orders(
    request: Request,
    db: Session = Depends(get_db),
) -> list[OrderRead]:
    service = OrderService(db, request.app)
    return [OrderRead.model_validate(order) for order in service.list_orders()]


@router.post(
    "/orders/{order_id}/fulfill",
    response_model=OrderRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_manual_fulfillment(
    order_id: str,
    payload: ManualFulfillRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> OrderRead:
    service = OrderService(db, request.app)
    order = service.trigger_manual_fulfillment(order_id, payload, background_tasks)
    return OrderRead.model_validate(order)


@test_router.post("/reset", response_model=ResetResponse)
def reset_demo_state() -> ResetResponse:
    reset_db()
    return ResetResponse(message="Demo state has been reset")
