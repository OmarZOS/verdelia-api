# Verdelia API Business Logic

This document describes the business behavior currently implemented in the API codebase. It is a code trace, not a product specification: where the implementation is incomplete, duplicated, or inconsistent, that is called out explicitly.

## 1. System Shape

The API is a FastAPI application assembled in [api_server/server.py](api_server/server.py).

```text
HTTP request
  -> middleware and exception handlers
  -> router endpoint and Pydantic API model
  -> domain service
  -> repository or external client
  -> SQLAlchemy/storage broker or remote service
  -> response model / serialized ORM object
```

The principal layers are:

| Layer | Responsibility | Main location |
| --- | --- | --- |
| Application | App factory, middleware, lifespan, router registration, health endpoints | [api_server/server.py](api_server/server.py) |
| Routers | HTTP paths, query/body parsing, dependency injection, thin orchestration | [api_server/routers](api_server/routers) |
| Services | Validation, calculations, state transitions, workflow coordination | [api_server/services](api_server/services) |
| Repositories | Entity-specific persistence queries and writes | [api_server/repositories](api_server/repositories) |
| Storage | SQLAlchemy engine/session handling, pagination, error translation | [api_server/storage/storage_broker.py](api_server/storage/storage_broker.py) and [api_server/storage/wrappers](api_server/storage/wrappers) |
| Domain models | ORM entities and request/response schemas | [api_server/core/models](api_server/core/models) |
| Integrations | Auth server, Finance, Inventory, AI, notifications, product observers | [api_server/features](api_server/features), [api_server/storage/wrappers](api_server/storage/wrappers), [api_server/communication](api_server/communication) |

Each request normally creates a service instance through a FastAPI dependency. Services create repositories and integration clients as needed. There is no single unit-of-work exposed at the router layer; transactional behavior is implemented per repository/storage helper or per workflow.

## 2. Application Startup and Request Processing

### Startup

`create_app()` performs the following steps:

1. Creates the FastAPI application with `/api/docs`, `/api/redoc`, and `/api/openapi.json`.
2. Adds Prometheus instrumentation outside the configured production mode.
3. Registers configured exception handlers.
4. Adds GZip, Trusted Host, session, CORS, and request logging middleware.
5. Includes all routers under `/api/v1` when `USE_VERSIONING` is enabled, otherwise `/api`.
6. Adds `/`, `/health`, `/ready`, and `/metrics` endpoints.

The lifespan calls `seed_database_if_needed()` during startup. The seed module populates reference data and development users through services; it is intended for development/test initialization.

### Middleware behavior

The request logger assigns or propagates an `X-Request-ID`, stores it in `request.state`, measures elapsed time, and returns `X-Process-Time` and `X-Request-ID`. CORS, session cookies, trusted hosts, and compression are configuration-driven.

### Health behavior

- `/` returns API identity and documentation URLs.
- `/health` is a liveness response and always reports healthy.
- `/ready` checks `check_database_connection()` and `check_cache_connection()`, but both helpers currently return `True` unconditionally.
- `/metrics` is exposed by the Prometheus instrumentator when enabled. The manually defined endpoint is effectively a placeholder and may overlap the instrumentator endpoint.

## 3. Authentication and Identity

### Password login

`POST /api/v1/authentication/token` accepts `AuthData_API` and calls `AuthService.login_user()`.

1. The API delegates credential verification to the configured auth client/server.
2. The returned identity and upstream tokens are placed into a local JWT payload.
3. A local access JWT and local refresh JWT are created.
4. The response includes token data, expiry, user ID, username, email, and person names.

The implementation therefore has two token layers: the upstream auth result is embedded in the locally created access token, while API authorization is performed by the local JWT dependency.

### JWT authorization

Protected routes use dependencies in [auth_dependencies.py](api_server/services/helpers/auth/auth_dependencies.py). The dependency:

- Requires a Bearer header.
- Decodes with `AUTH_SECRET_KEY` and `AUTH_ALGORITHM`.
- Accepts access tokens for normal endpoints and can be configured to accept refresh tokens for refresh endpoints.
- Manually checks expiry and requires `app_user_id`.
- Exposes helpers such as `get_current_user_id()` and `get_current_user_info()`.

The verifier contains a fallback that decodes without signature validation if normal decoding raises a JWT error. This is a security-sensitive behavior and should be treated as a deployment risk until removed or tightly constrained.

### OAuth

`GET /login/{provider}` validates the provider through `OAuthConfigService`, creates an OAuth client, and redirects to the provider. `GET /auth/{provider}` handles the callback, obtains user information through `AuthService`, and redirects to a `verdelia://auth/callback` deep link containing encoded data or an error.

Supported providers declared by `AuthService` are Google, Facebook, and Instagram. Provider configuration and actual callback behavior are delegated to the auth client/configuration services.

### User lifecycle

`UserService` and `PersonService` manage users, people, locations, and related profile data. User creation can create or attach person and location records and may associate an OAuth provider. User deletion delegates to the service/repository layer; the router exposes a `force_delete` parameter, but the shown endpoint does not pass that value into the service.

## 4. Domain Model and Relationships

The main commerce entities are defined in [models.py](api_server/core/models/models.py) and represented at the API boundary by [api_models.py](api_server/core/models/api_models.py).

```text
AppUser -> Person -> Location -> Address
AppUser -> ProductProvider / ProviderOrganisation
ProductProvider -> Product -> Iproduct / ProductCategory
ProductProvider -> ProvidedService -> requirements

Cart -> OrderedItem -> Product -> ProductProvider
Cart -> OrderedService -> ProvidedService -> ProductProvider
Cart -> Invoice -> Payment / Deposit / Receipt

PlacedOrder -> OrderedItem -> Product
PlacedOrder -> Invoice -> Payment
PlacedOrder -> Delivery -> Address / provider

Recipe -> RecipeContainsIngredient -> Ingredient
Person -> Patient -> Serology / Symptoms
User -> Reactions / Comments / Notifications
```

The README also records two commerce paths: ordered items may belong directly to a placed order or to a cart, while ordered services currently use the cart path. Carts can contain both product items and service bookings.

## 5. Commerce Workflows

### 5.1 Cart creation

`POST /api/v1/business/carts` enters `CartService.create_cart()`.

1. Rejects an empty cart. A cart must contain at least one product item or service.
2. Validates provider, seller, and optional buyer users.
3. Loads all products and services in bulk and rejects missing entities.
4. Builds a reservation plan. Product quantities come from ordered items; consumable service resources come from service resource requirements.
5. Calls Inventory `POST /inventory/stock/bulk` to validate availability without reserving.
6. Builds the cart, ordered items, ordered services, optional client person, prices, VAT, and service resource consumptions.
7. Creates an unpaid invoice, persists the cart, and persists ordered items/services with the cart ID.
8. Calls Inventory `POST /inventory/reserve` using persisted ordered-item and consumption IDs.
9. Releases ordered-item reservations if a later service-consumption reservation fails.

The cart workflow creates an invoice but does not automatically create or confirm payment. Payment/deposit operations are separate financial endpoints.

Cart reads provide filtered lists, detailed summaries, product item details, and service details. The summary calculates product quantity times unit price and adds service totals; it reports the stored cart total when present.

### 5.2 Order creation

`POST /api/v1/business/orders` enters `OrderService.create_order()` and is the most distributed workflow.

```text
Validate user
  -> Inventory bulk availability check
  -> Load products and calculate item totals
  -> Create placed order and ordered items
  -> Build deliveries by provider
  -> Create unpaid invoice
  -> Inventory reserve
  -> Finance create payment
  -> Finance confirm payment
  -> Mark invoice paid
  -> Inventory confirm/deduct
  -> Move order to PROCESSING
```

Important rules:

- The authenticated user ID replaces the user ID supplied in the order body.
- Every product must exist and every requested quantity must be available.
- Item total is quantity times product price times `(1 + applied_vat)`; order discount is subtracted and the result is clamped at zero.
- Orders can have multiple provider-specific deliveries. A new destination address can be created when no existing address ID is supplied.
- Invoice due date is 30 days after issue date and the invoice tax field is set to 19.
- Payment is created and immediately confirmed through Finance, then the local invoice is marked paid.
- Inventory is reserved before payment and confirmed/deducted after payment.
- Successful orders move to `PROCESSING`.

On failure, `_rollback_order_creation()` attempts to release inventory, refund a created payment, delete delivery, delete invoice, delete items, and delete the order. Rollback is best effort and can itself fail. The local variable tracking the created delivery is not assigned in the shown creation path, so delivery cleanup may not occur for a partially completed order.

### 5.3 Order state machine

`OrderService` accepts `PENDING`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, and `REFUNDED`.

```text
PENDING    -> PROCESSING, CANCELLED
PROCESSING -> SHIPPED, CANCELLED
SHIPPED    -> DELIVERED, CANCELLED, REFUNDED
DELIVERED  -> REFUNDED
CANCELLED  -> terminal
REFUNDED   -> terminal
```

Updates validate both the target status and the transition. Deletion asynchronously asks Inventory to release the order reservations, then deletes order items and the order locally.

### 5.4 Financial settlement

`FinancialService` and the financial router manage local payments, deposits, and additional fees. The endpoints support creation and filtered retrieval by invoice, cart, provider, or user. Finance integration used by checkout additionally supports payment creation, confirmation, rejection, refund, and invoice-payment queries through [finance_client.py](api_server/storage/wrappers/finance_client.py).

The data model supports both full payments linked to invoices and deposits linked to carts/invoices. The README describes carts moving from unpaid to deposited to paid, including multiple deposits, but the API does not centralize that state machine in one service; callers coordinate the separate financial endpoints.

### 5.5 Delivery

`DeliveryService` validates delivery data and status transitions, builds delivery models, and supports creation, retrieval, update, status changes, assignment, and deletion. Delivery records can be sourced from a placed order or a cart and carry a provider, address, fee, shipping method, and status. Order creation builds provider-specific delivery objects directly; the dedicated delivery router handles later operational changes.

## 6. Catalog and Provider Management

### Products and inventory-facing catalog

`ProductService` and `ProductRepository` provide:

- Product retrieval by ID, category, provider, user, and pagination.
- Product category retrieval.
- Product create/update/delete and image URL operations.
- `Iproduct` lookup by barcode.
- Product image upload/recognition paths.

Barcode lookup is DB-first: `GET /products/barcode/{barcode}` queries `Iproduct`, then calls `AIService.generate_product_info_by_barcode()` when no record exists and converts the AI response back to an `Iproduct` schema. The DB-only route skips AI. Image search sends uploaded bytes to `AIService.recognize_product_from_image()`.

Product updates can notify subscribers through the communication publisher. `GET /products/observer/{product_id}` opens an SSE stream, registers an asyncio queue, yields update events, and removes the subscriber on cancellation.

### Suppliers and organisations

`SupplierService` coordinates supplier CRUD, supplier types, organisations, images, and location/search delegates. Supplier validation checks referenced supplier types and organisations; image helpers handle provider and organisation images. Supplier routes expose both provider and organisation operations plus location-based supplier search.

### Provided services

`ServiceService` manages provided services, categories, staff roles, resource requirements, staff requirements, activation, and deletion. Creation:

1. Validates the referenced provider and category.
2. Maps API schemas to ORM models.
3. Persists the service.
4. Persists resource and staff requirement rows.

Deletion checks package-item and ordered-service dependencies before removing a service. Service listing supports category, provider, active-only, and pagination filters. Service prices are used by cart creation; consumable resource requirements become inventory reservations.

## 7. Staff, Business, and Operations

Staff assignments are represented by `ManagementRule`. `ManagementRuleService` delegates validation, CRUD, notifications, and rule queries to the rule delegate modules.

Supported behavior includes:

- Listing by organisation/provider/user/rule/status.
- User assignments, provider staff, and pending invitations.
- Creating and updating assignments.
- Accepting or rejecting invitations.
- Deleting assignments with dependency/status checks.

Invitation creation triggers notification building/sending. Status values exposed by the router are `ACTIVE`, `PENDING`, `REJECTED`, and `EXPIRED`.

Business routes create or retrieve provider/business records. `BusinessOperationService` exposes operational records through the business operation router. Detailed authorization for provider/staff ownership should be verified in the service/delegate implementations before treating route parameters as authorization boundaries.

## 8. Health and Wellness

The health routers expose person, blood-type, location, recipes, serology, symptoms, and patient history operations.

- `PersonService` creates/updates people, links locations/addresses, retrieves full or basic records, and manages blood types.
- `RecipeService` manages recipes, categories, ingredients, recipe ingredients, and images. Updating a recipe synchronizes its ingredient links.
- `MedicalService` manages serology indicators/results and symptoms/occurrences for patients, including history queries.
- `LocationService` validates coordinates, builds addresses and locations, and supports delivery/location records.

These domains are primarily synchronous CRUD plus relationship synchronization. They do not participate in the order payment saga unless a caller explicitly connects their records through the commerce APIs.

## 9. Social, Notifications, and Search

### Notifications

`NotificationService` validates and persists notifications, retrieves user notifications, marks one or all as read, counts unread notifications, deletes one/all, and supports invitation/bulk creation. Rule invitation workflows use notification helpers to construct recipient-facing messages.

### Reactions

`ReactionService` validates the reaction value/rating, validates the target entity and user, maps the reaction type to the appropriate ORM model, and supports create, update/delete, statistics, and bulk operations. Targets include products, recipes, providers, and comments.

### Search

`SearchService` searches products, recipes, users, people, suppliers, and related entity types. Router-level validation rejects search tokens shorter than two characters. Search methods apply offset/limit and query entity-specific name, description, contact, or person fields.

## 10. Persistence and Error Handling

Repositories call `storage_broker` for reads and the insertion helpers for writes. The broker:

- Validates offset and limit, with a default maximum of 1000.
- Obtains the configured SQLAlchemy engine.
- Delegates SQL operations to the SQL wrapper.
- Converts storage, integrity, not-found, and unexpected errors into `APIException` instances.

Services add domain-specific exceptions such as `ProductNotFoundException`, `OrderConflictException`, `InsufficientStockException`, and `ServiceNotFoundException`. The global exception setup maps these to consistent HTTP responses. Some routers instead convert exceptions directly to `HTTPException`, so response shapes are not completely uniform.

## 11. External and Asynchronous Boundaries

| Boundary | Used by | Purpose |
| --- | --- | --- |
| Auth server/client | `AuthService`, user creation/login | Credential verification and OAuth identity |
| Inventory/SILO | `OrderService`, `CartService`, `StockManager` | Availability, reserve, confirm/deduct, release |
| Finance service | `OrderService`, financial flows | Payment lifecycle, refunds, transaction details |
| AI provider | `AIService`, product routes | Barcode product generation and image recognition |
| SSE subscribers | `ProductService`, product observer route | Real-time product update delivery |
| Communication broker | Integration clients and publishers | HTTP requests and product update events |

The order and cart workflows are asynchronous because they call remote services. Inventory and Finance responses are normalized from several possible JSON shapes, which makes the integration tolerant but also hides contract drift when an unexpected response is treated as successful.

## 12. Route Families

With versioning enabled, the primary route groups are:

| Prefix/family | Domain |
| --- | --- |
| `/api/v1/authentication`, `/api/v1/login`, `/api/v1/auth` | Login, refresh/logout/profile, OAuth |
| `/api/v1/app_user`, `/api/v1/person` | Users and social profile records |
| `/api/v1/business` | Orders, carts, deliveries, services, finance, operations |
| `/api/v1/products`, `/api/v1/suppliers`, `/api/v1/staff` | Catalog, providers, staff rules |
| `/api/v1/people`, `/api/v1/serology`, `/api/v1/symptoms` | Health/person data |
| `/api/v1/recipes` | Recipes and ingredients |
| `/api/v1/addresses`, `/api/v1/location` | Address/location management |
| `/api/v1/notifications`, `/api/v1/reactions` | User-facing interactions |
| `/api/v1/search` | Cross-domain search |

The exact paths and endpoint parameters are defined in the router modules under [api_server/routers](api_server/routers). Some router files, including document, medical, and location routers, are present in the repository but are not all included by `server.py`; only routers explicitly included there are active in the application instance.

## 13. Observed Caveats and Follow-up Risks

These are implementation observations from the trace, not assumptions about intended product behavior:

1. Readiness checks are stubs and can report ready when the database or cache is unavailable.
2. JWT verification has an unsigned decode fallback. This should not be enabled for production authorization.
3. The server compares `settings.DEBUG` to `"PRODUCTION"` in several inverted-looking expressions, so logging, metrics, debug handlers, and reload behavior should be verified against the intended environment semantics.
4. CORS defaults allow all origins while credentials are enabled; production settings must override this.
5. The order saga performs several remote and local side effects without a distributed transaction. Rollback is compensating logic and is not guaranteed to restore every boundary.
6. Order delivery objects are built but the created-delivery tracking variable is not assigned in the shown path, weakening rollback cleanup.
7. Cart creation persists the invoice/cart before final inventory reservation and has limited compensating cleanup for failures after persistence.
8. Some route parameters such as user IDs are accepted from the URL without an obvious ownership check in the router; service-level authorization should be audited.
9. Pagination is inconsistently enforced at routes, services, and repositories. Some route parameters are declared but not passed through.
10. There are duplicated or contradictory implementations in portions of the service/repository code, for example duplicate `_build_staff_requirement` and `get_services_by_category` definitions. Python uses the later definition.
11. Response models are disabled or omitted for many endpoints, so ORM objects and dictionaries can produce inconsistent public response shapes.
12. The repository contains disabled or unregistered routers and placeholder services. Documentation should be regenerated when those routers become active.

## 14. Recommended Verification Paths

The highest-value integration checks are:

1. Login, access-token validation, refresh-token rejection on access routes, and OAuth callback failure paths.
2. Cart creation with products, services with consumable resources, insufficient stock, and reservation failure cleanup.
3. Order creation through inventory availability, reservation, Finance payment confirmation, inventory confirmation, and each rollback branch.
4. Order status transition acceptance/rejection and cancellation/refund behavior.
5. Ownership checks for user, cart, order, provider, staff, notification, and reaction endpoints.
6. Readiness behavior with unavailable database/cache dependencies.
