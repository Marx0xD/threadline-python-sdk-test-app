from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.threadline_lab import get_threadline_lab_db
from app.models.threadline_db_lab import (
    DbLabAuditLog,
    DbLabOrder,
    DbLabOrderItem,
    DbLabUser,
)
from app.schemas.threadline_db_lab import (
    AuditLogCreate,
    ChaoticOrderCreate,
    OrderCreate,
    OrderItemCreate,
    OrderItemPatch,
    OrderPatch,
    UserCreate,
    UserPatch,
)


router = APIRouter(prefix="/api/threadline-db-lab", tags=["threadline-db-lab"])


def _user_data(user: DbLabUser) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "status": user.status,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _order_data(order: DbLabOrder) -> dict[str, Any]:
    return {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "note": order.note,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


def _item_data(item: DbLabOrderItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "order_id": item.order_id,
        "sku": item.sku,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _audit_log_data(log: DbLabAuditLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "order_id": log.order_id,
        "action": log.action,
        "message": log.message,
        "created_at": log.created_at,
    }


def _get_user_or_404(db: Session, user_id: str) -> DbLabUser:
    user = db.get(DbLabUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DB lab user not found")
    return user


def _get_order_or_404(db: Session, order_id: str) -> DbLabOrder:
    order = db.get(DbLabOrder, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DB lab order not found")
    return order


def _get_item_or_404(db: Session, item_id: str) -> DbLabOrderItem:
    item = db.get(DbLabOrderItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DB lab order item not found")
    return item


def _recalculate_order_total(db: Session, order_id: str) -> None:
    total = db.scalar(
        select(func.coalesce(func.sum(DbLabOrderItem.quantity * DbLabOrderItem.unit_price), 0)).where(
            DbLabOrderItem.order_id == order_id
        )
    )
    order = db.get(DbLabOrder, order_id)
    if order is not None:
        order.total_amount = float(total or 0)


@router.get("/users")
def list_users(db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    users = list(db.scalars(select(DbLabUser).order_by(DbLabUser.created_at.desc())))
    return {
        "routePurpose": "List test-only DB lab users.",
        "expectedTelemetryPattern": "Simple SELECT with ordering.",
        "data": [_user_data(user) for user in users],
        "counts": {"users": len(users)},
    }


@router.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    user = _get_user_or_404(db, user_id)
    return {
        "routePurpose": "Fetch one test-only DB lab user.",
        "expectedTelemetryPattern": "Single primary-key lookup.",
        "data": _user_data(user),
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    user = DbLabUser(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "routePurpose": "Create one test-only DB lab user.",
        "expectedTelemetryPattern": "INSERT plus refresh SELECT.",
        "data": _user_data(user),
    }


@router.patch("/users/{user_id}")
def patch_user(
    user_id: str,
    payload: UserPatch,
    db: Session = Depends(get_threadline_lab_db),
) -> dict[str, Any]:
    user = _get_user_or_404(db, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return {
        "routePurpose": "Patch one test-only DB lab user.",
        "expectedTelemetryPattern": "SELECT, UPDATE, refresh SELECT.",
        "data": _user_data(user),
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: Session = Depends(get_threadline_lab_db)) -> Response:
    user = _get_user_or_404(db, user_id)
    orders = list(db.scalars(select(DbLabOrder).where(DbLabOrder.user_id == user_id)))
    for order in orders:
        for item in list(db.scalars(select(DbLabOrderItem).where(DbLabOrderItem.order_id == order.id))):
            db.delete(item)
        for log in list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.order_id == order.id))):
            db.delete(log)
        db.delete(order)
    for log in list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.user_id == user_id))):
        db.delete(log)
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/orders")
def list_orders(db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    orders = list(db.scalars(select(DbLabOrder).order_by(DbLabOrder.created_at.desc())))
    return {
        "routePurpose": "List test-only DB lab orders.",
        "expectedTelemetryPattern": "Simple SELECT with ordering.",
        "data": [_order_data(order) for order in orders],
        "counts": {"orders": len(orders)},
    }


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    order = _get_order_or_404(db, order_id)
    return {
        "routePurpose": "Fetch one test-only DB lab order.",
        "expectedTelemetryPattern": "Single primary-key lookup.",
        "data": _order_data(order),
    }


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    _get_user_or_404(db, payload.user_id)
    order = DbLabOrder(**payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    return {
        "routePurpose": "Create one test-only DB lab order.",
        "expectedTelemetryPattern": "User existence SELECT, INSERT, refresh SELECT.",
        "data": _order_data(order),
    }


@router.patch("/orders/{order_id}")
def patch_order(
    order_id: str,
    payload: OrderPatch,
    db: Session = Depends(get_threadline_lab_db),
) -> dict[str, Any]:
    order = _get_order_or_404(db, order_id)
    changes = payload.model_dump(exclude_unset=True)
    if "user_id" in changes and changes["user_id"] is not None:
        _get_user_or_404(db, changes["user_id"])
    for field, value in changes.items():
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return {
        "routePurpose": "Patch one test-only DB lab order.",
        "expectedTelemetryPattern": "SELECT, optional user SELECT, UPDATE, refresh SELECT.",
        "data": _order_data(order),
    }


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: str, db: Session = Depends(get_threadline_lab_db)) -> Response:
    order = _get_order_or_404(db, order_id)
    for item in list(db.scalars(select(DbLabOrderItem).where(DbLabOrderItem.order_id == order_id))):
        db.delete(item)
    for log in list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.order_id == order_id))):
        db.delete(log)
    db.delete(order)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/orders/{order_id}/items")
def list_order_items(order_id: str, db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    _get_order_or_404(db, order_id)
    items = list(
        db.scalars(
            select(DbLabOrderItem)
            .where(DbLabOrderItem.order_id == order_id)
            .order_by(DbLabOrderItem.created_at.asc())
        )
    )
    return {
        "routePurpose": "List test-only DB lab order items.",
        "expectedTelemetryPattern": "Order lookup plus child collection SELECT.",
        "data": [_item_data(item) for item in items],
        "counts": {"orderItems": len(items)},
    }


@router.post("/orders/{order_id}/items", status_code=status.HTTP_201_CREATED)
def create_order_item(
    order_id: str,
    payload: OrderItemCreate,
    db: Session = Depends(get_threadline_lab_db),
) -> dict[str, Any]:
    _get_order_or_404(db, order_id)
    item = DbLabOrderItem(order_id=order_id, **payload.model_dump())
    db.add(item)
    db.flush()
    _recalculate_order_total(db, order_id)
    db.commit()
    db.refresh(item)
    return {
        "routePurpose": "Create a test-only DB lab order item and recalculate the order total.",
        "expectedTelemetryPattern": "Order SELECT, INSERT, aggregate SELECT, UPDATE, refresh SELECT.",
        "data": _item_data(item),
    }


@router.patch("/order-items/{item_id}")
def patch_order_item(
    item_id: str,
    payload: OrderItemPatch,
    db: Session = Depends(get_threadline_lab_db),
) -> dict[str, Any]:
    item = _get_item_or_404(db, item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.flush()
    _recalculate_order_total(db, item.order_id)
    db.commit()
    db.refresh(item)
    return {
        "routePurpose": "Patch a test-only DB lab order item and recalculate the order total.",
        "expectedTelemetryPattern": "SELECT, UPDATE, aggregate SELECT, order UPDATE, refresh SELECT.",
        "data": _item_data(item),
    }


@router.delete("/order-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_item(item_id: str, db: Session = Depends(get_threadline_lab_db)) -> Response:
    item = _get_item_or_404(db, item_id)
    order_id = item.order_id
    db.delete(item)
    db.flush()
    _recalculate_order_total(db, order_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-logs")
def list_audit_logs(db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    logs = list(db.scalars(select(DbLabAuditLog).order_by(DbLabAuditLog.created_at.desc())))
    return {
        "routePurpose": "List test-only DB lab audit logs.",
        "expectedTelemetryPattern": "Simple SELECT with ordering.",
        "data": [_audit_log_data(log) for log in logs],
        "counts": {"auditLogs": len(logs)},
    }


@router.get("/users/{user_id}/audit-logs")
def list_user_audit_logs(
    user_id: str,
    db: Session = Depends(get_threadline_lab_db),
) -> dict[str, Any]:
    _get_user_or_404(db, user_id)
    logs = list(
        db.scalars(
            select(DbLabAuditLog)
            .where(DbLabAuditLog.user_id == user_id)
            .order_by(DbLabAuditLog.created_at.desc())
        )
    )
    return {
        "routePurpose": "List audit logs for one test-only DB lab user.",
        "expectedTelemetryPattern": "User lookup plus filtered audit-log SELECT.",
        "data": [_audit_log_data(log) for log in logs],
        "counts": {"auditLogs": len(logs)},
    }


@router.post("/audit-logs", status_code=status.HTTP_201_CREATED)
def create_audit_log(
    payload: AuditLogCreate,
    db: Session = Depends(get_threadline_lab_db),
) -> dict[str, Any]:
    if payload.user_id is not None:
        _get_user_or_404(db, payload.user_id)
    if payload.order_id is not None:
        _get_order_or_404(db, payload.order_id)
    log = DbLabAuditLog(**payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return {
        "routePurpose": "Create one test-only DB lab audit log.",
        "expectedTelemetryPattern": "Optional parent SELECTs, INSERT, refresh SELECT.",
        "data": _audit_log_data(log),
    }


@router.get("/problems/users-with-orders-n-plus-one")
def users_with_orders_n_plus_one(db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    # Intentionally inefficient for Threadline DB telemetry testing: do not optimize this route.
    users = list(db.scalars(select(DbLabUser).order_by(DbLabUser.created_at.desc())))
    data = []
    order_count = 0
    item_count = 0
    for user in users:
        orders = list(db.scalars(select(DbLabOrder).where(DbLabOrder.user_id == user.id)))
        order_count += len(orders)
        order_data = []
        for order in orders:
            items = list(db.scalars(select(DbLabOrderItem).where(DbLabOrderItem.order_id == order.id)))
            item_count += len(items)
            order_data.append({**_order_data(order), "items": [_item_data(item) for item in items]})
        data.append({**_user_data(user), "orders": order_data})

    return {
        "routePurpose": "Intentionally create an N+1 users/orders/items query pattern.",
        "expectedTelemetryPattern": "One users query, one orders query per user, one items query per order.",
        "intentionalProblems": ["N+1 queries", "Nested child lookups inside loops"],
        "data": data,
        "counts": {"users": len(users), "orders": order_count, "orderItems": item_count},
    }


@router.get("/problems/users-with-orders-optimized")
def users_with_orders_optimized(db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    users = list(
        db.scalars(
            select(DbLabUser)
            .options(selectinload(DbLabUser.orders).selectinload(DbLabOrder.items))
            .order_by(DbLabUser.created_at.desc())
        )
    )
    data = []
    order_count = 0
    item_count = 0
    for user in users:
        orders = []
        for order in user.orders:
            order_count += 1
            item_count += len(order.items)
            orders.append({**_order_data(order), "items": [_item_data(item) for item in order.items]})
        data.append({**_user_data(user), "orders": orders})

    return {
        "routePurpose": "Return users with orders and items using a batched loading strategy.",
        "expectedTelemetryPattern": "Batched SELECTs instead of per-row child queries.",
        "data": data,
        "counts": {"users": len(users), "orders": order_count, "orderItems": item_count},
    }


@router.get("/problems/orders/{order_id}/duplicate-lookups")
def duplicate_order_lookups(
    order_id: str,
    db: Session = Depends(get_threadline_lab_db),
) -> dict[str, Any]:
    # Intentionally inefficient for Threadline DB telemetry testing: do not remove duplicates.
    first_order = _get_order_or_404(db, order_id)
    second_order = db.scalar(select(DbLabOrder).where(DbLabOrder.id == order_id))
    third_order = db.get(DbLabOrder, order_id)
    user = db.get(DbLabUser, first_order.user_id)
    logs = list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.order_id == order_id)))
    duplicate_logs = list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.order_id == order_id)))

    return {
        "routePurpose": "Fetch the same entities more than needed to test duplicate query telemetry.",
        "expectedTelemetryPattern": "Repeated order and audit-log lookups, plus avoidable user lookup.",
        "intentionalProblems": ["Duplicate queries", "Avoidable separate lookup instead of join"],
        "data": {
            "firstOrder": _order_data(first_order),
            "secondOrderFound": second_order is not None,
            "thirdOrderFound": third_order is not None,
            "user": _user_data(user) if user else None,
            "auditLogs": [_audit_log_data(log) for log in logs],
            "duplicateAuditLogCount": len(duplicate_logs),
        },
        "counts": {"auditLogs": len(logs), "duplicateAuditLogs": len(duplicate_logs)},
    }


@router.get("/problems/orders/{order_id}/brittle-details")
def brittle_order_details(order_id: str, db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    # Intentionally brittle for Threadline DB telemetry testing: this mimics messy production code.
    order = _get_order_or_404(db, order_id)
    user = db.get(DbLabUser, order.user_id)
    items = list(db.scalars(select(DbLabOrderItem).where(DbLabOrderItem.order_id == order_id)))
    logs = list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.order_id == order_id)))
    branches_taken = []

    if not items:
        branches_taken.append("no_items_fallback_audit_lookup")
        logs = list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.order_id == order_id)))
        if user is not None:
            branches_taken.append("fallback_user_audit_lookup")
            user_logs = list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.user_id == user.id)))
        else:
            user_logs = []
    elif order.total_amount == 0:
        branches_taken.append("zero_total_recount_items")
        items = list(db.scalars(select(DbLabOrderItem).where(DbLabOrderItem.order_id == order_id)))
        user_logs = []
    elif order.status in {"failed", "cancelled", "stuck"}:
        branches_taken.append("problem_status_extra_log_lookup")
        user_logs = list(
            db.scalars(
                select(DbLabAuditLog).where(
                    DbLabAuditLog.user_id == order.user_id,
                    DbLabAuditLog.action.in_(["order_failed", "manual_review", "order_cancelled"]),
                )
            )
        )
    else:
        branches_taken.append("normal_but_still_chatty")
        user_logs = []
        if user is not None and user.status != "active":
            branches_taken.append("inactive_user_extra_order_lookup")
            list(db.scalars(select(DbLabOrder).where(DbLabOrder.user_id == user.id)))

    return {
        "routePurpose": "Exercise brittle, branch-heavy detail loading with extra queries.",
        "expectedTelemetryPattern": "Several small SELECTs with data-dependent extra queries.",
        "intentionalProblems": ["Brittle conditionals", "Redundant fallback queries", "Chatty detail loading"],
        "data": {
            "order": _order_data(order),
            "user": _user_data(user) if user else None,
            "items": [_item_data(item) for item in items],
            "auditLogs": [_audit_log_data(log) for log in logs],
            "userAuditLogs": [_audit_log_data(log) for log in user_logs],
            "branchesTaken": branches_taken,
        },
        "counts": {
            "orderItems": len(items),
            "auditLogs": len(logs),
            "userAuditLogs": len(user_logs),
        },
    }


@router.post("/problems/orders/chaotic-create", status_code=status.HTTP_201_CREATED)
def chaotic_create_order(
    payload: ChaoticOrderCreate,
    db: Session = Depends(get_threadline_lab_db),
) -> dict[str, Any]:
    try:
        _get_user_or_404(db, payload.user_id)
        order = DbLabOrder(user_id=payload.user_id, status=payload.status, note=payload.note)
        db.add(order)
        db.flush()

        created_items = []
        total = 0.0
        for item_payload in payload.items:
            item = DbLabOrderItem(order_id=order.id, **item_payload.model_dump())
            db.add(item)
            db.flush()
            created_items.append(item)
            total += item.quantity * item.unit_price
        order.total_amount = total

        log = DbLabAuditLog(
            user_id=payload.user_id,
            order_id=order.id,
            action="chaotic_create",
            message="Created by the intentionally rollback-capable DB telemetry route.",
        )
        db.add(log)
        db.flush()

        if payload.fail_after_items:
            raise RuntimeError("Intentional rollback after creating order items")

        db.commit()
        db.refresh(order)
        return {
            "routePurpose": "Create an order, items, and audit log inside one transaction.",
            "expectedTelemetryPattern": "Transactional INSERTs followed by COMMIT.",
            "data": {
                "order": _order_data(order),
                "items": [_item_data(item) for item in created_items],
                "auditLog": _audit_log_data(log),
            },
            "counts": {"orderItems": len(created_items)},
        }
    except HTTPException:
        db.rollback()
        raise
    except RuntimeError as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "routePurpose": "Intentionally roll back a multi-table transaction.",
                "expectedTelemetryPattern": "Transactional INSERTs followed by ROLLBACK.",
                "intentionalProblems": ["Transaction rollback after partial work"],
                "error": str(exc),
                "data": {"rolledBack": True},
            },
        )


@router.get("/problems/reports/slow-summary")
def slow_summary(db: Session = Depends(get_threadline_lab_db)) -> dict[str, Any]:
    # Intentionally inefficient for Threadline DB telemetry testing: keep this chatty and loop-heavy.
    user_count = db.scalar(select(func.count()).select_from(DbLabUser)) or 0
    order_count = db.scalar(select(func.count()).select_from(DbLabOrder)) or 0
    order_item_count = db.scalar(select(func.count()).select_from(DbLabOrderItem)) or 0
    all_orders = list(db.scalars(select(DbLabOrder)))

    total_amount = 0.0
    orders_by_status: dict[str, int] = {}
    for order in all_orders:
        total_amount += order.total_amount
        orders_by_status[order.status] = orders_by_status.get(order.status, 0) + 1
        list(db.scalars(select(DbLabAuditLog).where(DbLabAuditLog.order_id == order.id)))

    return {
        "routePurpose": "Generate a deliberately slow report using many small queries.",
        "expectedTelemetryPattern": "Multiple count queries, full order scan, loop-based aggregation, per-order log lookups.",
        "intentionalProblems": ["Chatty reporting queries", "Loop aggregation instead of SQL aggregation"],
        "data": {
            "totalOrderAmount": total_amount,
            "ordersByStatus": orders_by_status,
        },
        "counts": {
            "users": user_count,
            "orders": order_count,
            "orderItems": order_item_count,
        },
    }
