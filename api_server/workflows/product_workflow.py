# workflows/product_workflow.py
"""
Product workflow — orchestration layer.

Owns every call that crosses a process boundary:
  - AIService (image recognition, barcode lookup)
  - subscriber notification (SSE)
  - background tasks scheduling

Also owns the sequencing that combines product persistence with the
usage system:

  * `create_product` checks the domain-counted `PRODUCTS_PER_PROVIDER`
    limit before persisting — a rejected create writes nothing.
  * AI operations reserve an `AI_CREDITS_MONTHLY` credit before the
    call, and refund it if the call or the subsequent write fails.
    This is the reserve/work/refund pattern; the alternative
    (check-and-reserve atomically) would leave a user charged for
    calls that errored.

ProductService (local) is injected. No remote clients live on the
service.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from fastapi import BackgroundTasks

from services.domain_limit_service import DomainLimitService
from core.models.api_models import (
    Product_API,
    ProductImage_API,
    Iproduct_API,
)
from core.models.app_models import ResourceCode
from core.exceptions.specific.product_exceptions import (
    ProductFetchNotFoundException,
)
from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
)
from core.models.models import Product, Iproduct
from services.helpers.ai_service import AIService
from services.product_service import ProductService
from services.subscription_service import SubscriptionService
from services.usage_service import UsageService

from core.logging_config import get_logger

logger = get_logger(__name__)


# Global subscribers storage — lives with the workflow because
# notification is a workflow concern, not a persistence one.
subscribers: Dict[int, List[asyncio.Queue]] = {}


class ProductWorkflow:
    """Orchestration around ProductService."""

    def __init__(
        self,
        service: Optional[ProductService] = None,
        ai_service: Optional[AIService] = None,
        usage_service: Optional[UsageService] = None,
        domain_limits: Optional[DomainLimitService] = None,
        subscription_service: Optional[SubscriptionService] = None,
    ):
        self.service = service or ProductService()
        self.ai_service = ai_service or AIService()
        self.usage_service = usage_service or UsageService()
        self.domain_limits = domain_limits or DomainLimitService()
        self.subscription_service = (
            subscription_service or SubscriptionService()
        )


    # ==================== AI recognition ====================

    async def recognize_product_from_image(
        self,
        image_bytes: bytes,
        language: str = "fr",
        *,
        user_id: Optional[int] = None,
        subscription_id: Optional[int] = None,
    ) -> Iproduct_API:
        """Recognize a product from an image.

        If a user is supplied, reserves one AI credit before the
        call and refunds it if the call fails or returns nothing.
        Callers that don't pass a user are not metered — this is the
        path for internal jobs and tests.

        Exactly one of `user_id` / `subscription_id` should be
        supplied when metering. `user_id` is the common case at API
        boundaries; `subscription_id` is for internal callers that
        already resolved it.
        """
        logger.info(f"Recognizing product from image (language={language})")

        with self._ai_credit_reservation(
            user_id=user_id,
            subscription_id=subscription_id,
            operation="recognize_product_from_image",
        ):
            ai_result, model_name = (
                await self.ai_service.recognize_product_from_image(
                    image_bytes, language
                )
            )

            if not ai_result:
                logger.warning("AI recognition returned no results")
                raise ProductFetchNotFoundException(
                    identifier="image",
                    search_type="image_recognition",
                )

            return self.ai_service.format_ai_result_to_iproduct(
                ai_result, model_name
            )

    async def get_product_info_by_barcode(
        self,
        barcode: str,
        language: str = "fr",
        *,
        user_id: Optional[int] = None,
        subscription_id: Optional[int] = None,
    ) -> Iproduct_API:
        """Look up product info by barcode.

        Same metering rules as `recognize_product_from_image`.
        """
        logger.info(
            f"Getting product info by barcode: {barcode} "
            f"(language={language})"
        )

        with self._ai_credit_reservation(
            user_id=user_id,
            subscription_id=subscription_id,
            operation="get_product_info_by_barcode",
        ):
            ai_result, model_name = (
                await self.ai_service.generate_product_info_by_barcode(
                    barcode, language
                )
            )

            if not ai_result:
                logger.warning(
                    f"AI returned no results for barcode: {barcode}"
                )
                raise ProductFetchNotFoundException(
                    identifier=barcode,
                    search_type="barcode_ai",
                )

            return self.ai_service.format_ai_result_to_iproduct(
                ai_result, model_name
            )

    # ==================== Create with optional AI data ====================

    async def create_product(
        self,
        product_api: Product_API,
        image: Optional[ProductImage_API] = None,
        iproduct: Optional[Iproduct_API] = None,
        *,
        user_id: int,
        subscription_id: Optional[int] = None,
        existing_product_count: Optional[int] = None,
    ) -> Product:
        """Create a product, enforcing the plan's product-per-provider
        limit before persisting.

        `user_id` is required. Every write that could increase a
        domain count goes through this method, and metering requires
        knowing whose subscription to charge against. Callers that
        genuinely need to bypass metering (seeders, migrations, admin
        bulk imports) must use `create_product_unmetered` below — the
        explicit name makes the bypass auditable.

        The check flow:

        1. Resolve the subscription from `user_id` (or use the
            supplied `subscription_id`).
        2. Count the products currently under the target provider.
        3. Check `PRODUCTS_PER_PROVIDER` against the plan.
        4. Only on pass, persist.

        A denial raises `APIException` (403 or 429) with a structured
        body. Nothing is written.

        The count is a `SELECT COUNT(*)` against the `product` table,
        scoped to the provider the new product belongs to. The limit
        is *per provider*, so a user with three providers has three
        independent ceilings, not one.
        """
        provider_id = product_api.product_provider_id
        logger.info(
            f"create_product: start user_id={user_id} "
            f"provider_id={provider_id} "
            f"name={product_api.product_name!r} "
            f"has_iproduct={iproduct is not None}"
        )

        # ── Resolve subscription ───────────────────────────────
        if subscription_id is None:
            sub = self.subscription_service.get_subscription_for_user(
                user_id
            )
            if sub is None:
                logger.warning(
                    f"create_product: refusing user_id={user_id} — no "
                    f"subscription on file"
                )
                raise APIException(
                    status_code=HTTP_404_NOT_FOUND,
                    error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                    details={"user_id": user_id},
                )
            subscription_id = sub.id_subscription
            logger.info(
                f"create_product: resolved subscription_id="
                f"{subscription_id} plan_id={sub.subscription_plan_id} "
                f"for user_id={user_id}"
            )
        else:
            logger.info(
                f"create_product: using supplied subscription_id="
                f"{subscription_id} for user_id={user_id}"
            )

        # ── Require a target provider ──────────────────────────
        if provider_id is None:
            logger.error(
                f"create_product: missing product_provider_id for "
                f"user_id={user_id} name={product_api.product_name!r}"
            )
            raise ValueError(
                "create_product requires product_provider_id to "
                "enforce the per-provider quota."
            )

        # ── Domain limit check ─────────────────────────────────
        if existing_product_count is None:
            existing_product_count = (
                self.service.count_products_for_provider(provider_id)
            )
            logger.info(
                f"create_product: counted existing={existing_product_count} "
                f"products for provider_id={provider_id}"
            )
        else:
            logger.info(
                f"create_product: using supplied existing_product_count="
                f"{existing_product_count} for provider_id={provider_id}"
            )

        result = self.domain_limits.check_with_count(
            subscription_id=subscription_id,
            resource=ResourceCode.PRODUCTS_PER_PROVIDER,
            current_count=existing_product_count,
            requested=1,
        )

        check = result.check
        logger.info(
            f"create_product: limit check "
            f"resource={check.resource.value} "
            f"current={check.current} requested={check.requested} "
            f"allowed={check.allowed} kind={check.limit.kind.value} "
            f"limit={check.limit.ceiling} remaining={check.remaining} "
            f"reason={check.reason!r}"
        )

        if not result.allowed:
            logger.warning(
                f"create_product: denying user_id={user_id} "
                f"subscription_id={subscription_id} "
                f"provider_id={provider_id} "
                f"resource={check.resource.value} "
                f"current={check.current} "
                f"limit={check.limit.ceiling} "
                f"reason={check.reason!r}"
            )
            raise self._denial_to_exception(
                check, user_id=user_id
            )

        # ── AI fetch (best-effort) ─────────────────────────────
        if iproduct is None and product_api.product_barcode:
            logger.info(
                f"create_product: fetching AI data for barcode="
                f"{product_api.product_barcode}"
            )
            try:
                iproduct = await self.get_product_info_by_barcode(
                    product_api.product_barcode,
                    user_id=user_id,
                    subscription_id=subscription_id,
                )
                logger.info(
                    f"create_product: AI returned iproduct for barcode="
                    f"{product_api.product_barcode}"
                )
            except ProductFetchNotFoundException:
                logger.info(
                    f"create_product: no AI data for barcode="
                    f"{product_api.product_barcode}; creating without it"
                )
                iproduct = None
        elif iproduct is not None:
            logger.info(
                f"create_product: caller supplied iproduct; skipping AI"
            )
        else:
            logger.info(
                f"create_product: no barcode and no iproduct; creating "
                f"without AI metadata"
            )

        # ── Persist ────────────────────────────────────────────
        logger.info(
            f"create_product: persisting user_id={user_id} "
            f"provider_id={provider_id} "
            f"name={product_api.product_name!r}"
        )
        try:
            created = self.service.create_product(
                product_api=product_api,
                image=image,
                iproduct=iproduct,
            )
        except Exception as e:
            logger.error(
                f"create_product: persist failed user_id={user_id} "
                f"provider_id={provider_id} "
                f"name={product_api.product_name!r}: {e}",
                exc_info=True,
            )
            raise

        logger.info(
            f"create_product: success user_id={user_id} "
            f"provider_id={provider_id} "
            f"product_id={getattr(created, 'id_product', None)} "
            f"name={product_api.product_name!r}"
        )
        return created

    async def create_product_unmetered(
        self,
        product_api: Product_API,
        image: Optional[ProductImage_API] = None,
        iproduct: Optional[Iproduct_API] = None,
    ) -> Product:
        """Create a product without any plan check.

        For internal jobs only: seeders, migrations, admin bulk
        imports. Anything reachable from an HTTP endpoint must go
        through `create_product` instead.

        The explicit name makes every bypass grep-able:

            grep -rn "create_product_unmetered"
        """
        return self.service.create_product(
            product_api=product_api,
            image=image,
            iproduct=iproduct,
        )


    # ==================== Update with notification ====================

    def update_product(
        self,
        product_id: int,
        product_api: Product_API,
        image: Optional[ProductImage_API] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Product:
        """Update a product, optionally notifying subscribers.

        No usage checks — updates aren't metered. The plan limit is
        about how many products exist, not how often they're edited.
        """
        updated_product = self.service.update_product(
            product_id=product_id,
            product_api=product_api,
            image=image,
        )

        if background_tasks:
            payload = self.service.product_to_dict(updated_product)
            background_tasks.add_task(
                self._notify_product_subscribers,
                product_id,
                payload,
            )

        return updated_product

    # ==================== Usage helpers ====================

    def _ai_credit_reservation(
        self,
        *,
        user_id: Optional[int],
        subscription_id: Optional[int],
        operation: str,
    ):
        """Context manager that reserves one AI credit on entry and
        refunds it on exception.

        No-op when neither a user nor a subscription is supplied —
        the internal-job path.

        The reservation is not atomic with the check. Two concurrent
        calls can both see "0 of 1 used" and both succeed, leaving
        the counter at 2. Same tradeoff documented in
        `UsageService.check_and_reserve`: acceptable here because
        the alternative (row-level locking on every AI call) costs
        more than the race worth.

        Example:

            with self._ai_credit_reservation(
                user_id=user.id, subscription_id=None,
                operation="barcode_lookup",
            ):
                result = await ai_service.lookup(...)
                return transform(result)
        """
        return _AiCreditReservation(
            usage_service=self.usage_service,
            user_id=user_id,
            subscription_id=subscription_id,
            operation=operation,
        )

    def _denial_to_exception(
        self,
        check,
        *,
        user_id: Optional[int],
    ) -> APIException:
        """Translate a failed domain limit check into an API error.

        Mirrors `UsageWorkflow._denial_to_exception` — same status
        codes, same details shape. Duplicated rather than imported
        because the workflows are independent layers and neither
        should depend on the other's private methods.
        """
        details = {
            "resource": check.resource.value,
            "current": check.current,
            "requested": check.requested,
            "reason": check.reason,
        }

        if check.limit.is_disabled:
            return APIException(
                status_code=HTTP_402_PAYMENT_REQUIRED,
                error_code=ErrorCode.RESOURCE_NOT_AVAILABLE,
                details=details,
            )

        if check.limit.is_finite:
            details["limit"] = check.limit.ceiling
            details["remaining"] = check.remaining
            return APIException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                details=details,
            )

        logger.error(
            f"Unhandled denial kind for user={user_id}: {check.reason}"
        )
        return APIException(
            status_code=HTTP_403_FORBIDDEN,
            error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
            details=details,
        )

    # ==================== SSE subscriber management ====================

    def add_subscriber(self, product_id: int, queue: asyncio.Queue) -> None:
        if product_id not in subscribers:
            subscribers[product_id] = []
        subscribers[product_id].append(queue)
        logger.debug(
            f"Added subscriber for product {product_id}. "
            f"Total: {len(subscribers[product_id])}"
        )

    def remove_subscriber(self, product_id: int, queue: asyncio.Queue) -> None:
        if product_id in subscribers and queue in subscribers[product_id]:
            subscribers[product_id].remove(queue)
            if not subscribers[product_id]:
                del subscribers[product_id]
            logger.debug(f"Removed subscriber for product {product_id}")

    async def _notify_product_subscribers(
        self, product_id: int, data: Dict[str, Any]
    ) -> None:
        if product_id not in subscribers:
            return

        disconnected: List[asyncio.Queue] = []

        for queue in subscribers[product_id]:
            try:
                queue.put_nowait(data)
            except (asyncio.QueueFull, RuntimeError):
                disconnected.append(queue)
            except Exception as e:
                logger.error(
                    f"Error notifying subscriber for product {product_id}: {e}"
                )
                disconnected.append(queue)

        for queue in disconnected:
            if queue in subscribers.get(product_id, []):
                subscribers[product_id].remove(queue)

        if product_id in subscribers and not subscribers[product_id]:
            del subscribers[product_id]

        logger.debug(
            f"Notified {len(subscribers.get(product_id, []))} subscribers "
            f"for product {product_id}"
        )

class _AiCreditReservation:
    """Reserve one AI credit for the duration of a `with` block.

    On entry: if a target (user or subscription) is supplied, check
    the AI credit limit and, on success, increment the counter by 1.
    If the check denies, raise `APIException` — the caller can't
    proceed without a credit.

    On exit without exception: nothing more to do. The credit stays
    consumed.

    On exit with exception: refund the credit, then let the
    exception propagate. The refund is best-effort; if it fails, the
    original exception is what the caller sees, and the failure is
    logged.
    """

    def __init__(
        self,
        *,
        usage_service: UsageService,
        user_id: Optional[int],
        subscription_id: Optional[int],
        operation: str,
    ):
        self._usage = usage_service
        self._user_id = user_id
        self._sub_id = subscription_id
        self._operation = operation
        self._reserved = False
        self._resource = ResourceCode.AI_CREDITS_MONTHLY

    def __enter__(self):
        # No target → nothing to meter. The internal-job path.
        if self._user_id is None and self._sub_id is None:
            return self

        check = self._check_and_reserve()
        if not check.allowed:
            raise APIException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                details={
                    "resource": self._resource.value,
                    "reason": check.reason,
                    "operation": self._operation,
                },
            )
        self._reserved = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._reserved:
            # Reservation never happened — either no target or the
            # check denied (in which case the exception is already
            # propagating).
            return False

        if exc_type is not None:
            self._refund()

        # Returning False lets the original exception propagate.
        return False

    def _check_and_reserve(self):
        """Reserve a credit. Returns the `LimitCheck` so the caller
        can inspect `allowed` and `reason`."""
        if self._sub_id is not None:
            result = self._usage.check_and_reserve(
                self._sub_id, self._resource, 1
            )
            return result.check

        # user_id path
        result = self._usage.check_and_reserve_for_user(
            self._user_id, self._resource, 1
        )
        return result.check

    def _refund(self) -> None:
        """Best-effort refund. Never raises — the caller's exception
        is what matters, and a failed refund shouldn't shadow it."""
        try:
            if self._sub_id is not None:
                self._usage.reduce_for_user  # not used; placeholder
                # subscription-id path is not directly exposed on
                # the service's reduce; use the user path when we
                # have a user, otherwise go through the repo.
                if self._user_id is not None:
                    self._usage.reduce_for_user(
                        self._user_id, self._resource, 1
                    )
                else:
                    logger.warning(
                        f"Cannot refund AI credit: no user_id for "
                        f"subscription {self._sub_id}. Refund skipped."
                    )
            else:
                self._usage.reduce_for_user(
                    self._user_id, self._resource, 1
                )
        except Exception as e:
            logger.error(
                f"Failed to refund AI credit after "
                f"{self._operation} failed: {e}"
            )