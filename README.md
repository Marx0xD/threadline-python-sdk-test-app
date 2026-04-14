# orderflow-demo

`orderflow-demo` is a small FastAPI application that simulates an e-commerce order workflow with enough moving parts to produce useful debugging and investigation traces.

It exercises:

- inbound HTTP request handling
- service orchestration and state transitions
- background fulfillment jobs
- outbound HTTP calls to fake downstream services
- duplicate and missing-step workflow bugs
- realistic workflow failure scenarios for observability and debugging tools

## Project layout

```text
app/
  api/routes/          # Public and internal HTTP endpoints
  clients/             # Outbound HTTP client used by the workflow
  core/                # Settings
  db/                  # SQLAlchemy engine and sessions
  models/              # SQLAlchemy models
  repositories/        # Persistence helpers
  schemas/             # Pydantic request/response models
  services/            # Order orchestration and fulfillment logic
```

## Requirements

- Python 3.12+

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optionally copy the environment template:

```bash
cp .env.example .env
```

PowerShell alternative:

```powershell
Copy-Item .env.example .env
```

4. Start the server:

```bash
uvicorn app.main:app --reload
```

5. Open the docs at `http://127.0.0.1:8000/docs`.

## Workflow

`POST /orders` runs the first half of the workflow inline:

1. receive request
2. create the order in SQLite
3. reserve inventory over an internal HTTP call
4. authorize payment over an internal HTTP call
5. mark the order as `processing`
6. enqueue a background fulfillment job

The fulfillment job then:

1. marks shipment as `queued`
2. calls the fake shipment service
3. updates shipment to `shipped`
4. marks the order as `fulfilled`

## Failure toggles

All toggles live under the optional `simulation` object on `POST /orders` and `POST /orders/{order_id}/fulfill`.

```json
{
  "customer_id": "cust-123",
  "item_sku": "sku-blue-shirt",
  "quantity": 2,
  "amount": 49.99,
  "simulation": {
    "inventory_fail": false,
    "payment_fail": false,
    "missing_fulfillment": false,
    "duplicate_fulfillment": false,
    "swallow_fulfillment_exception": false,
    "shipment_fail": false,
    "slow_inventory_seconds": 0,
    "slow_payment_seconds": 0,
    "slow_shipment_seconds": 0
  }
}
```

Useful scenarios:

- `inventory_fail`: inventory reservation fails and the order becomes `failed`
- `payment_fail`: payment authorization fails and the order becomes `failed`
- `missing_fulfillment`: order reaches `processing` but no fulfillment job is queued
- `duplicate_fulfillment`: fulfillment is enqueued twice to trigger duplicate handling
- `swallow_fulfillment_exception`: fulfillment catches an exception and leaves the order stuck
- `slow_inventory_seconds` or `slow_payment_seconds`: adds artificial latency to downstream calls
- `shipment_fail`: optional extra late-stage failure during fulfillment

## Sample curl commands

Create a healthy order:

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"cust-001\",\"item_sku\":\"sku-red-mug\",\"quantity\":1,\"amount\":19.99}"
```

Create an order with slow payment plus duplicate fulfillment:

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"cust-002\",\"item_sku\":\"sku-headphones\",\"quantity\":1,\"amount\":129.99,\"simulation\":{\"slow_payment_seconds\":2,\"duplicate_fulfillment\":true}}"
```

Create an order that gets stuck because fulfillment never runs:

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"cust-003\",\"item_sku\":\"sku-sneakers\",\"quantity\":1,\"amount\":89.99,\"simulation\":{\"missing_fulfillment\":true}}"
```

Create an order with a swallowed background exception:

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"cust-004\",\"item_sku\":\"sku-gift-box\",\"quantity\":1,\"amount\":39.99,\"simulation\":{\"swallow_fulfillment_exception\":true}}"
```

List all orders:

```bash
curl http://127.0.0.1:8000/orders
```

Fetch a single order:

```bash
curl http://127.0.0.1:8000/orders/<order_id>
```

Manually trigger fulfillment:

```bash
curl -X POST http://127.0.0.1:8000/orders/<order_id>/fulfill \
  -H "Content-Type: application/json" \
  -d "{}"
```

Reset demo state:

```bash
curl -X POST http://127.0.0.1:8000/test/reset
```
