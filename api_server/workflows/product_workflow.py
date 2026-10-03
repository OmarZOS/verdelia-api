# workflows/product_workflow.py
"""
Product workflow — orchestration layer.

Owns every call that crosses a process boundary:
  - AIService (image recognition, barcode lookup)
  - subscriber notification (SSE)
  - background tasks scheduling

Owns the sequencing of multi-step operations that span more than one
local service call.

ProductService (local) is injected. No remote clients live on the service.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import BackgroundTasks

from core.models.api_models import (
    Product_API,
    ProductImage_API,
    Iproduct_API,
)
from core.exceptions.specific.product_exceptions import (
    ProductFetchNotFoundException,
)
from core.models.models import Product, Iproduct
from services.helpers.ai_service import AIService
from services.product_service import ProductService

from core.logging_config import get_logger

logger = get_logger(__name__)


# Global subscribers storage — lives with the workflow because notification
# is a workflow concern, not a persistence one.
subscribers: Dict[int, List[asyncio.Queue]] = {}


class ProductWorkflow:
    """Orchestration around ProductService."""

    def __init__(
        self,
        service: Optional[ProductService] = None,
        ai_service: Optional[AIService] = None,
    ):
        self.service = service or ProductService()
        self.ai_service = ai_service or AIService()

    # ==================== AI recognition ====================

    async def recognize_product_from_image(
        self, image_bytes: bytes, language: str = "fr"
    ) -> Iproduct_API:
        logger.info(f"Recognizing product from image (language={language})")

        ai_result, model_name = await self.ai_service.recognize_product_from_image(
            image_bytes, language
        )

        if not ai_result:
            logger.warning("AI recognition returned no results")
            raise ProductFetchNotFoundException(
                identifier="image",
                search_type="image_recognition",
            )

        return self.ai_service.format_ai_result_to_iproduct(ai_result, model_name)

    async def get_product_info_by_barcode(
        self, barcode: str, language: str = "fr"
    ) -> Iproduct_API:
        logger.info(f"Getting product info by barcode: {barcode} (language={language})")

        ai_result, model_name = await self.ai_service.generate_product_info_by_barcode(
            barcode, language
        )

        if not ai_result:
            logger.warning(f"AI returned no results for barcode: {barcode}")
            raise ProductFetchNotFoundException(
                identifier=barcode,
                search_type="barcode_ai",
            )

        return self.ai_service.format_ai_result_to_iproduct(ai_result, model_name)

    # ==================== Create with optional AI data ====================

    async def create_product(
        self,
        product_api: Product_API,
        image: Optional[ProductImage_API] = None,
        iproduct: Optional[Iproduct_API] = None,
    ) -> Product:
        """
        Orchestrates:
          1. If `iproduct` is None but the barcode is present, optionally
             fetch AI data first.
          2. Call the local service to persist.
        """
        if iproduct is None and product_api.product_barcode:
            try:
                iproduct = await self.get_product_info_by_barcode(
                    product_api.product_barcode
                )
            except ProductFetchNotFoundException:
                # AI lookup is best-effort on create. The product can be
                # created without AI metadata.
                logger.info(
                    f"No AI data for barcode {product_api.product_barcode}; "
                    f"creating without it."
                )
                iproduct = None

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
        """
        Orchestrates:
          1. Local service update.
          2. If `background_tasks` is provided, schedule subscriber
             notification.
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