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


#Expected body schema: {'$defs': {'SimulationConfig': {'properties': {'inventory_fail': {'default': False, 'title': 'Inventory Fail', 'type': 'boolean'}, 'payment_fail': {'default': False, 'title': 'Payment Fail', 'type': 'boolean'}, 'missing_fulfillment': {'default': False, 'title': 'Missing Fulfillment', 'type': 'boolean'}, 'duplicate_fulfillment': {'default': False, 'title': 'Duplicate Fulfillment', 'type': 'boolean'}, 'swallow_fulfillment_exception': {'default': False, 'title': 'Swallow Fulfillment Exception', 'type': 'boolean'}, 'shipment_fail': {'default': False, 'title': 'Shipment Fail', 'type': 'boolean'}, 'slow_inventory_seconds': {'default': 0, 'maximum': 30, 'minimum': 0, 'title': 'Slow Inventory Seconds', 'type': 'number'}, 'slow_payment_seconds': {'default': 0, 'maximum': 30, 'minimum': 0, 'title': 'Slow Payment Seconds', 'type': 'number'}, 'slow_shipment_seconds': {'default': 0, 'maximum': 30, 'minimum': 0, 'title': 'Slow Shipment Seconds', 'type': 'number'}}, 'title': 'SimulationConfig', 'type': 'object'}}, 'properties': {'order_id': {'title': 'Order Id', 'type': 'string'}, 'item_sku': {'title': 'Item Sku', 'type': 'string'}, 'quantity': {'exclusiveMinimum': 0, 'title': 'Quantity', 'type': 'integer'}, 'simulation': {'$ref': '#/$defs/SimulationConfig'}}, 'required': ['order_id', 'item_sku', 'quantity', 'simulation'], 'title': 'ShipmentCreateRequest', 'type': 'object'}
class ShipmentCreateRequest(BaseModel):
    order_id: str
    item_sku: str
    quantity: int = Field(gt=0)
    simulation: SimulationConfig


class DownstreamResponse(BaseModel):
    ok: bool
    reference: str | None = None
    message: str | None = None
