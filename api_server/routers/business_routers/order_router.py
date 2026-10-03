# routers/business_routers/order_router.py
"""
Order router.

Routing rules:
  - Endpoints that cross a process boundary (inventory silo, finance
    service) depend on OrderWorkflow.
  - Endpoints that only touch local entities depend on OrderService.

Router never instantiates either directly — both come from dependency
providers, so tests can override them.
"""

from fastapi import APIRouter, Depends, Query, status, HTTPException
from typing import List

import logging

from services.helpers.auth.auth_dependencies import get_current_user_id
from core.models.api_models import (
    Delivery_Info_API,
    OrderedItem_API,
    PlacedOrder_API,
)
from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.order_exceptions import (
    OrderNotFoundException,
    OrderCreationFailedException,
    OrderUpdateFailedException,
    OrderDeleteFailedException,
    OrderItemsNotFoundException,
    InvalidOrderStatusException,
    OrderConflictException,
    OrderStatusTransitionException,
)
from core.exceptions.specific.product_exceptions import (
    ProductNotFoundException,
    ProductQuantityNotEnoughException,
)
from core.exceptions.handler import UserNotFoundException
from services.order_service import OrderService
from workflows.order_workflow import OrderWorkflow

from core.logging_config import get_logger

logger = get_logger(__name__)


order_router = APIRouter()


# ==================== Dependency providers ====================

def get_order_service() -> OrderService:
    """Local operations only: reads, writes, validations, persistence."""
    return OrderService()


def get_order_workflow() -> OrderWorkflow:
    """Cross-boundary orchestration: inventory + finance."""
    return OrderWorkflow()


# ==================== Order CRUD endpoints ====================

@order_router.post(
    "/orders",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    description=(
        "Creates a new order. Orchestrates inventory availability check, "
        "local persistence, and inventory reservation. Payment and "
        "inventory deduction are deferred to their respective endpoints."
    ),
    responses={
        201: {"description": "Order created successfully"},
        400: {"model": ErrorResponseModel, "description": "Bad request"},
        404: {"model": ErrorResponseModel, "description": "Resource not found"},
        409: {"model": ErrorResponseModel, "description": "Conflict — insufficient stock"},
        **get_crud_error_responses(include_404=True, include_409=True),
    },
)
async def create_order(
    ordered_items: List[OrderedItem_API],
    submitted_order: PlacedOrder_API,
    payment_method: str = Query(
        "cash", description="Payment method: card, cash, bank_transfer"
    ),
    delivery_info: Delivery_Info_API = None,
    user_id: int = Depends(get_current_user_id),
    workflow: OrderWorkflow = Depends(get_order_workflow),
):
    """
    Create a new order.

    Workflow responsibilities:
      1. Validate items
      2. Check inventory availability (remote)
      3. Persist order, invoice, deliveries (local)
      4. Reserve inventory (remote)

    Deferred to other endpoints:
      - Payment      → POST /orders/{order_id}/pay
      - Deduction    → POST /orders/{order_id}/confirm-inventory
    """
    logger.info(
        f"Creating new order for user: {submitted_order.ordering_user_id}"
    )

    if not ordered_items:
        raise OrderCreationFailedException(
            error="Order must have at least one item",
            user_id=submitted_order.ordering_user_id,
        )

    try:
        submitted_order.ordering_user_id = user_id

        quantities, order, result = await workflow.create_order(
            items=ordered_items,
            order_data=submitted_order,
            payment_method=payment_method,
            user_id=submitted_order.ordering_user_id,
            delivery_data=delivery_info,
        )

        logger.info(f"Order created successfully with ID: {order.id_placed_order}")

        return {
            "order": order,
            "payment_id": result.get('payment_id'),
            "invoice_id": result.get('invoice_id'),
            "payment_status": result.get('payment_status'),
            "inventory_reserved": result.get('inventory_reserved'),
            "inventory_deducted": result.get('inventory_deducted', False),
        }

    except UserNotFoundException:
        logger.error(
            f"User {submitted_order.ordering_user_id} not found"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {submitted_order.ordering_user_id} not found",
        )
    except ProductNotFoundException as e:
        logger.error(f"Product not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {e.product_id} not found",
        )
    except ProductQuantityNotEnoughException as e:
        logger.error(f"Insufficient stock: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Insufficient stock for product {e.product_id}. "
                f"Available: {e.available}, Requested: {e.requested}"
            ),
        )
    except (OrderCreationFailedException, OrderConflictException):
        raise
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        raise OrderCreationFailedException(
            error=str(e),
            user_id=submitted_order.ordering_user_id,
        )


@order_router.post(
    "/orders/{order_id}/pay",
    summary="Process payment for an order",
    description=(
        "Creates and confirms a payment for an order, marks the invoice "
        "paid, and advances the order to PROCESSING. Idempotent on already-"
        "paid invoices."
    ),
    responses={
        200: {"description": "Payment processed"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
async def process_order_payment(
    order_id: int,
    payment_method: str = Query("card", description="Payment method"),
    user_id: int = Depends(get_current_user_id),
    workflow: OrderWorkflow = Depends(get_order_workflow),
):
    """
    Phase 2 of the order workflow.
    """
    logger.info(f"Processing payment for order {order_id}")

    try:
        result = await workflow.process_payment(
            order_id=order_id,
            payment_method=payment_method,
        )
        return result

    except OrderNotFoundException:
        raise
    except OrderUpdateFailedException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to process payment for order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing failed: {e}",
        )


@order_router.post(
    "/orders/{order_id}/confirm-inventory",
    summary="Confirm inventory for an order",
    description=(
        "Converts reserved inventory into a real deduction. Call after "
        "payment succeeds. Idempotent — already-confirmed items are ignored."
    ),
    responses={
        200: {"description": "Inventory confirmed"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
async def confirm_order_inventory(
    order_id: int,
    user_id: int = Depends(get_current_user_id),
    workflow: OrderWorkflow = Depends(get_order_workflow),
):
    """
    Phase 3 of the order workflow.
    """
    logger.info(f"Confirming inventory for order {order_id}")

    try:
        return await workflow.confirm_inventory_for_order(order_id)
    except OrderNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm inventory for order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inventory confirmation failed: {e}",
        )


@order_router.post(
    "/orders/{order_id}/finalize",
    summary="Finalize an order (payment + inventory)",
    description=(
        "Convenience endpoint that runs payment and inventory confirmation "
        "back-to-back. Use when the caller wants the synchronous behavior."
    ),
    responses={
        200: {"description": "Order finalized"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
async def finalize_order(
    order_id: int,
    payment_method: str = Query("card", description="Payment method"),
    user_id: int = Depends(get_current_user_id),
    workflow: OrderWorkflow = Depends(get_order_workflow),
):
    logger.info(f"Finalizing order {order_id}")

    try:
        return await workflow.finalize_order(
            order_id=order_id,
            payment_method=payment_method,
        )
    except OrderNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to finalize order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Finalization failed: {e}",
        )


# ==================== Local reads (service only) ====================

@order_router.get(
    "/orders/user/{user_id}",
    summary="Get user orders",
    description="Get all orders for a specific user with pagination",
    responses={
        200: {"description": "Orders retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
def get_user_orders(
    user_id: int,
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records"),
    order_service: OrderService = Depends(get_order_service),
):
    """Local-only: reads orders for a user."""
    logger.info(
        f"Fetching orders for user {user_id} (offset={offset}, limit={limit})"
    )

    try:
        orders, total = order_service.get_user_orders(user_id, offset, limit)
        return {
            "data": orders,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total,
                "next_offset": offset + limit if offset + limit < total else None,
            },
        }
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    except Exception as e:
        logger.error(f"Failed to fetch orders for user {user_id}: {e}")
        raise OrderNotFoundException(
            user_id=user_id, details={"error": str(e)}
        )


@order_router.get(
    "/orders/{order_id}",
    summary="Get order by ID",
    description="Retrieve a specific order with all details",
    responses={
        200: {"description": "Order retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
def get_order(
    order_id: int,
    include_items: bool = Query(True, description="Include ordered items"),
    order_service: OrderService = Depends(get_order_service),
):
    """Local-only: reads an order and its associated records."""
    logger.info(f"Fetching order with ID: {order_id}")

    try:
        order = order_service.get_order_by_id(order_id, with_items=include_items)

        response = {"order": order}

        if include_items and hasattr(order, 'ordered_item'):
            response["items_count"] = len(order.ordered_item)

            try:
                invoice = order_service.invoice_repo.get_invoice_by_order(
                    order.id_placed_order
                )
                if invoice:
                    response["invoice"] = invoice

                delivery = order_service.delivery_repo.get_by_order(
                    order.id_placed_order
                )
                if delivery:
                    response["delivery"] = delivery
            except Exception as e:
                logger.warning(f"Could not fetch associated records: {e}")

        return response

    except OrderNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch order {order_id}: {e}")
        raise OrderNotFoundException(
            order_id=order_id, details={"error": str(e)}
        )


@order_router.get(
    "/orders/{order_id}/items",
    summary="Get order items",
    description="Retrieve all items in a specific order",
    responses={
        200: {"description": "Order items retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
def get_order_items(
    order_id: int,
    order_service: OrderService = Depends(get_order_service),
):
    """Local-only: reads items with product enrichment."""
    logger.info(f"Fetching items for order ID: {order_id}")

    try:
        order_service.get_order_by_id(order_id, with_items=True)
        items = order_service.get_order_items(order_id)

        items_with_details = []
        for item in items:
            item_dict = {
                "id": item.id_ordered_item,
                "product_id": item.ordered_product_id,
                "quantity": item.ordered_quantity,
                "unit_price": item.unit_price,
                "applied_vat": item.applied_vat,
                "total_price": (
                    item.ordered_quantity
                    * item.unit_price
                    * (1 + item.applied_vat)
                ),
            }

            try:
                product = order_service.product_repo.get_product_by_id(
                    item.ordered_product_id
                )
                if product:
                    item_dict["product_name"] = product.product_name
                    item_dict["product_brand"] = product.product_brand
                    item_dict["product_category"] = product.product_category_id
            except Exception as e:
                logger.warning(
                    f"Could not fetch product {item.ordered_product_id}: {e}"
                )

            items_with_details.append(item_dict)

        return {
            "order_id": order_id,
            "items": items_with_details,
            "total_items": len(items_with_details),
        }

    except OrderNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch items for order {order_id}: {e}")
        raise OrderItemsNotFoundException(
            order_id=order_id, details={"error": str(e)}
        )


# ==================== Local writes (service only) ====================

@order_router.put(
    "/orders/{order_id}",
    summary="Update an order",
    description=(
        "Update an order's metadata and items. Does not touch remote "
        "systems. If you need to release/re-reserve inventory, do it "
        "explicitly via the inventory endpoints."
    ),
    responses={
        200: {"description": "Order updated successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
def update_order(
    order_id: int,
    updated_items: List[OrderedItem_API],
    updated_order: PlacedOrder_API,
    user_id: int = Depends(get_current_user_id),
    order_service: OrderService = Depends(get_order_service),
):
    """Local-only: update order metadata and items."""
    logger.info(f"Updating order with ID: {order_id}")

    try:
        existing_order = order_service.get_order_by_id(
            order_id, with_items=False
        )

        if existing_order.ordering_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this order",
            )

        if updated_order.placed_order_state:
            current_status = getattr(
                existing_order, 'placed_order_state', 'PENDING'
            )
            try:
                order_service.validate_status_transition(
                    current_status,
                    updated_order.placed_order_state,
                )
            except OrderStatusTransitionException:
                raise InvalidOrderStatusException(
                    order_id=order_id,
                    current_status=current_status,
                    requested_status=updated_order.placed_order_state,
                    allowed_statuses=list(
                        order_service.STATUS_TRANSITIONS.get(
                            current_status, set()
                        )
                    ),
                )

        updated_order.id_placed_order = order_id
        result = order_service.update_order(
            order_id, updated_items, updated_order
        )

        logger.info(f"Order {order_id} updated successfully")
        return result

    except (
        OrderNotFoundException,
        InvalidOrderStatusException,
        OrderUpdateFailedException,
    ):
        raise
    except OrderStatusTransitionException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {e.current_status} to {e.new_status}",
        )
    except Exception as e:
        logger.error(f"Failed to update order {order_id}: {e}")
        raise OrderUpdateFailedException(
            order_id=order_id,
            error=str(e),
            fields_attempted=["items", "status", "details"],
        )


@order_router.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order",
    description=(
        "Deletes an order. Releases reserved inventory via the workflow, "
        "then removes local entities."
    ),
    responses={
        204: {"description": "Order deleted successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
async def delete_order(
    order_id: int,
    force_delete: bool = Query(
        False, description="Force delete even if order has items"
    ),
    user_id: int = Depends(get_current_user_id),
    workflow: OrderWorkflow = Depends(get_order_workflow),
    order_service: OrderService = Depends(get_order_service),
):
    """
    Cross-boundary delete: releases inventory remotely, then deletes
    locally. Uses both workflow (remote) and service (local guard checks).
    """
    logger.info(f"Deleting order with ID: {order_id} (force={force_delete})")

    try:
        order_service.get_order_by_id(order_id, with_items=True)

        items = order_service.get_order_items(order_id)
        if items and not force_delete:
            raise OrderDeleteFailedException(
                order_id=order_id,
                error=(
                    f"Order has {len(items)} items. "
                    f"Use force_delete=true to delete."
                ),
            )

        success = await workflow.delete_order(order_id)
        if not success:
            raise OrderDeleteFailedException(
                order_id=order_id, error="Service returned False"
            )

        logger.info(f"Order {order_id} deleted successfully")
        return None

    except (OrderNotFoundException, OrderDeleteFailedException):
        raise
    except Exception as e:
        logger.error(f"Failed to delete order {order_id}: {e}")
        raise OrderDeleteFailedException(order_id=order_id, error=str(e))


@order_router.patch(
    "/orders/{order_id}/status",
    summary="Update order status",
    description="Update only the status of an order. No inventory changes.",
    responses={
        200: {"description": "Order status updated successfully"},
        400: {"model": ErrorResponseModel, "description": "Invalid status or transition"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
def update_order_status(
    order_id: int,
    status: str = Query(..., description="New order status"),
    user_id: int = Depends(get_current_user_id),
    order_service: OrderService = Depends(get_order_service),
):
    """
    Local-only: status transition validated by the service.

    Valid transitions:
      PENDING    → PROCESSING, CANCELLED
      PROCESSING → SHIPPED, CANCELLED
      SHIPPED    → DELIVERED, CANCELLED, REFUNDED
      DELIVERED  → REFUNDED
      CANCELLED  → (none)
      REFUNDED   → (none)
    """
    valid_statuses = list(order_service.VALID_ORDER_STATUSES)

    if status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Valid statuses: {', '.join(valid_statuses)}",
        )

    logger.info(f"Updating status for order {order_id} to '{status}'")

    try:
        order = order_service.get_order_by_id(order_id, with_items=False)
        updated_order = order_service.update_order_status(
            order_id, status.upper()
        )

        return {
            "order_id": updated_order.id_placed_order,
            "previous_status": order.placed_order_state,
            "new_status": updated_order.placed_order_state,
            "updated_at": updated_order.placed_order_last_mod,
        }

    except OrderNotFoundException:
        raise
    except OrderStatusTransitionException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot transition from {e.current_status} to {e.new_status}. "
                f"Allowed: {', '.join(e.allowed_transitions)}"
            ),
        )
    except InvalidOrderStatusException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition from {e.current_status} "
                f"to {e.requested_status}"
            ),
        )
    except Exception as e:
        logger.error(f"Failed to update status for order {order_id}: {e}")
        raise OrderUpdateFailedException(
            order_id=order_id,
            error=str(e),
            fields_attempted=["status"],
        )


# ==================== Remote reads (workflow only) ====================

@order_router.get(
    "/orders/{order_id}/inventory-status",
    summary="Check inventory status for order items",
    description=(
        "Reads current stock availability from the inventory silo for "
        "every item in the order. Purely a read — no reservation."
    ),
    responses={
        200: {"description": "Inventory status retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
async def get_order_inventory_status(
    order_id: int,
    workflow: OrderWorkflow = Depends(get_order_workflow),
    order_service: OrderService = Depends(get_order_service),
):
    """
    Cross-boundary read: uses the service for local item lookup, and the
    workflow (which owns the inventory client) for remote stock reads.
    """
    logger.info(f"Checking inventory status for order {order_id}")

    try:
        order_service.get_order_by_id(order_id, with_items=True)
        items = order_service.get_order_items(order_id)

        inventory_status = []
        for item in items:
            try:
                status = await workflow.inventory_client.get_stock_status(
                    product_id=item.ordered_product_id
                )
                inventory_status.append({
                    "product_id": item.ordered_product_id,
                    "ordered_quantity": item.ordered_quantity,
                    "available_quantity": status.get('available_quantity', 0),
                    "reserved_quantity": status.get('reserved_quantity', 0),
                    "in_stock": (
                        status.get('available_quantity', 0)
                        >= item.ordered_quantity
                    ),
                })
            except Exception as e:
                logger.warning(
                    f"Could not check inventory for product "
                    f"{item.ordered_product_id}: {e}"
                )
                inventory_status.append({
                    "product_id": item.ordered_product_id,
                    "ordered_quantity": item.ordered_quantity,
                    "error": str(e),
                })

        return {
            "order_id": order_id,
            "items": inventory_status,
            "all_available": all(
                item.get('in_stock', False)
                for item in inventory_status
                if 'error' not in item
            ),
        }

    except OrderNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to check inventory for order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check inventory: {e}",
        )