from app.api.routes.internal import router as internal_router
from app.api.routes.orders import router as orders_router
from app.api.routes.orders import test_router

__all__ = ["internal_router", "orders_router", "test_router"]
