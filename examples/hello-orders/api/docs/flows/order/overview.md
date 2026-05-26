# Order domain — flow overview

The order domain in `hello-orders` covers a tiny happy path: a customer who already has a draft order adds one line item and places the order. There is no fulfillment, no payment, no refund.

## Place-order flow

The cross-domain scenario [`place-order.arazzo.yaml`](../../../specs/v1/scenarios/cross-domain/place-order.arazzo.yaml) drives this flow.

```mermaid
sequenceDiagram
  autonumber
  actor Customer
  participant API as REST API
  participant Bus as Event Bus<br/>(helloorders.events)

  Note over Customer,Bus: Setup: customer-with-draft-order recipe<br/>creates one Customer + one draft Order

  Customer->>API: GET /v1/orders/{orderId}
  API-->>Customer: 200 OK<br/>{ status: "draft", ... }

  Customer->>API: POST /v1/orders/{orderId}/lines<br/>{ description, quantity, unitPriceMinor }
  API-->>Customer: 201 Created<br/>OrderLine
  API->>Bus: OrderLine.Created<br/>(after snapshot)

  Customer->>API: POST /v1/orders/{orderId}/place
  API-->>Customer: 200 OK<br/>{ status: "placed", ... }
  Note right of API: x-trigger-when fires:<br/>After.status='placed' && Before.status='draft'
  API->>Bus: Order.Placed<br/>(before + after snapshots)
  Note right of API: Order.Updated is suppressed<br/>(mutual-exclusivity rule)

  loop until status == "placed"
    Customer->>API: GET /v1/orders/{orderId}
    API-->>Customer: 200 OK<br/>{ status: "placed" }
  end
```

## Key contract points

- **Single state transition** in this example: `draft → placed` via `placeOrder`. The state transition is the only path that emits `Order.Placed`.
- **Mutual exclusivity** between `Order.Placed` and `Order.Updated` is enforced by the `x-trigger-when` predicate on `OrderPlaced.yaml`. When the predicate matches, `Order.Updated` is not emitted for that save.
- **OrderLine.Created** is a plain `*Created` event — after snapshot only, no state transition.
- **Polling** in step 4 is illustrative; the response from step 3 already shows `status: placed`. The poll demonstrates the async-verify pattern from the kit's `scenario-samples.yaml`.

## Out of scope

- No `cancelOrder` (no `Order.Cancelled` event).
- No fulfillment or payment events.
- No `updateOrderLine` / `removeOrderLine` operations.

When the example grows to cover more of the order lifecycle, this flow doc grows alongside.
