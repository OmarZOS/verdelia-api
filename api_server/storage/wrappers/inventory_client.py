# storage/wrappers/inventory_client.py

from typing import Optional, List, Dict, Any
import json
import logging

from constants import SILO_SERVER_URL
from communication.communication_broker import (
    send_post_request,
    send_get_request,
    send_put_request,
    send_delete_request
)

from core.logging_config import get_logger

logger = get_logger(__name__)


class InventoryServiceClient:
    """Client for Inventory API"""
    
    base_url = SILO_SERVER_URL
    timeout = 30
    
    def _parse_response(self, response) -> Dict:
        """
        Parse HTTP response to JSON dictionary.
        Handles both Response objects and already parsed dicts.
        """
        try:
            # If response is already a dict, return it
            if isinstance(response, dict):
                return response
            
            # If response has .json() method, use it
            if hasattr(response, 'json'):
                try:
                    return response.json()
                except Exception as e:
                    logger.warning(f"Failed to parse response.json(): {e}")
            
            # If response has .text, try to parse it
            if hasattr(response, 'text'):
                try:
                    return json.loads(response.text)
                except Exception as e:
                    logger.warning(f"Failed to parse response.text: {e}")
            
            # If response is a string, try to parse it
            if isinstance(response, str):
                try:
                    return json.loads(response)
                except Exception as e:
                    logger.warning(f"Failed to parse response string: {e}")
            
            # If response has .content, try to parse it
            if hasattr(response, 'content'):
                try:
                    return json.loads(response.content.decode('utf-8'))
                except Exception as e:
                    logger.warning(f"Failed to parse response.content: {e}")
            
            # If we have a response object with status_code but no content
            if hasattr(response, 'status_code'):
                logger.warning(f"Response object with status {response.status_code} but no parsable content")
                return {"status_code": response.status_code, "success": False}
            
            # Return empty dict as fallback
            logger.warning(f"Could not parse response: {type(response)}")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return {}
    
    async def reserve_inventory(self, items: List[Dict], item_type: str = 'ordered_item') -> Dict:
        """Reserve inventory for ordered items or consumptions."""
        try:
            endpoint = f"{self.base_url}/inventory/reserve"
            
            request_data = {
                "items": items,
                "item_type": item_type
            }
            
            logger.info(f"Reserving {len(items)} {item_type}(s)")
            
            response = await send_post_request(
                endpoint=endpoint,
                json_data=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                logger.info(f"✅ Successfully reserved {len(items)} items")
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Reservation failed with status {status_code}: {parsed_response}")
                raise Exception(f"Reservation failed: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to reserve inventory: {e}")
            raise
    
    async def confirm_inventory(self, items: List[Dict], item_type: str = 'ordered_item') -> Dict:
        """Confirm inventory reservations (deduct from stock)."""
        try:
            endpoint = f"{self.base_url}/inventory/confirm"
            
            request_data = {
                "items": items,
                "item_type": item_type
            }
            
            logger.info(f"Confirming {len(items)} {item_type}(s)")
            
            response = await send_post_request(
                endpoint=endpoint,
                json_data=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                logger.info(f"✅ Successfully confirmed {len(items)} items")
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Confirmation failed with status {status_code}: {parsed_response}")
                raise Exception(f"Confirmation failed: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to confirm inventory: {e}")
            raise
    
    async def release_inventory(self, items: List[Dict], item_type: str = 'ordered_item') -> Dict:
        """Release inventory reservations (cancel reservation)."""
        try:
            endpoint = f"{self.base_url}/inventory/release"
            
            request_data = {
                "items": items,
                "item_type": item_type
            }
            
            logger.info(f"Releasing {len(items)} {item_type}(s)")
            
            response = await send_post_request(
                endpoint=endpoint,
                json_data=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                logger.info(f"✅ Successfully released {len(items)} items")
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Release failed with status {status_code}: {parsed_response}")
                raise Exception(f"Release failed: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to release inventory: {e}")
            raise
    
    async def check_and_reserve(self, items: List[Dict], item_type: str = 'ordered_item') -> Dict:
        """Check availability and reserve in one operation."""
        try:
            endpoint = f"{self.base_url}/inventory/check-and-reserve"
            
            request_data = {
                "items": items,
                "item_type": item_type
            }
            
            logger.info(f"Checking and reserving {len(items)} {item_type}(s)")
            
            response = await send_post_request(
                endpoint=endpoint,
                json_data=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                logger.info(f"✅ Successfully checked and reserved {len(items)} items")
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Check and reserve failed with status {status_code}: {parsed_response}")
                raise Exception(f"Check and reserve failed: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to check and reserve: {e}")
            raise
    
    async def get_stock_status(self, product_id: int) -> Dict:
        """Get stock status for a single product."""
        try:
            endpoint = f"{self.base_url}/inventory/stock/{product_id}"
            
            logger.info(f"Getting stock status for product {product_id}")
            
            response = await send_get_request(
                endpoint=endpoint,
                params={}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Failed to get stock status: {parsed_response}")
                raise Exception(f"Failed to get stock status: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to get stock status for product {product_id}: {e}")
            raise
    
    async def get_bulk_stock_status(self, product_ids: List[int]) -> Dict:
        """Get stock status for multiple products."""
        try:
            endpoint = f"{self.base_url}/inventory/stock/bulk"
            
            request_data = {"product_ids": product_ids}
            
            logger.info(f"Getting bulk stock status for {len(product_ids)} products")
            
            response = await send_post_request(
                endpoint=endpoint,
                json_data=request_data,
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"Bulk stock status response status: {getattr(response, 'status_code', 'unknown')}")
            
            # Parse the response first
            parsed_response = self._parse_response(response)
            logger.info(f"Parsed response: {parsed_response}")
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Failed to get bulk stock status: {parsed_response}")
                raise Exception(f"Failed to get bulk stock status: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to get bulk stock status: {e}")
            raise
    
    async def get_available_quantity(self, product_id: int) -> Dict:
        """Get available quantity for a product."""
        try:
            endpoint = f"{self.base_url}/inventory/available/{product_id}"
            
            logger.info(f"Getting available quantity for product {product_id}")
            
            response = await send_get_request(
                endpoint=endpoint,
                params={}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Failed to get available quantity: {parsed_response}")
                raise Exception(f"Failed to get available quantity: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to get available quantity for product {product_id}: {e}")
            raise
    
    async def bulk_reserve(self, ordered_items: List[Dict] = None, consumptions: List[Dict] = None) -> Dict:
        """Bulk reserve inventory for both ordered items and consumptions."""
        try:
            endpoint = f"{self.base_url}/inventory/bulk/reserve"
            
            request_data = {}
            if ordered_items:
                request_data["ordered_items"] = ordered_items
            if consumptions:
                request_data["consumptions"] = consumptions
            
            logger.info(f"Bulk reserving: {len(ordered_items or [])} ordered items, {len(consumptions or [])} consumptions")
            
            response = await send_post_request(
                endpoint=endpoint,
                json_data=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Bulk reservation failed: {parsed_response}")
                raise Exception(f"Bulk reservation failed: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to bulk reserve: {e}")
            raise
    
    async def bulk_confirm(self, ordered_items: List[Dict] = None, consumptions: List[Dict] = None) -> Dict:
        """Bulk confirm inventory for both ordered items and consumptions ATOMICALLY."""
        try:
            endpoint = f"{self.base_url}/inventory/bulk/confirm"
            
            request_data = {}
            if ordered_items:
                request_data["ordered_items"] = ordered_items
            if consumptions:
                request_data["consumptions"] = consumptions
            
            logger.info(f"Bulk confirming: {len(ordered_items or [])} ordered items, {len(consumptions or [])} consumptions")
            
            response = await send_post_request(
                endpoint=endpoint,
                json_data=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Bulk confirmation failed: {parsed_response}")
                raise Exception(f"Bulk confirmation failed: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to bulk confirm: {e}")
            raise
    
    async def bulk_release(self, ordered_items: List[Dict] = None, consumptions: List[Dict] = None) -> Dict:
        """Bulk release inventory for both ordered items and consumptions."""
        try:
            endpoint = f"{self.base_url}/inventory/bulk/release"
            
            request_data = {}
            if ordered_items:
                request_data["ordered_items"] = ordered_items
            if consumptions:
                request_data["consumptions"] = consumptions
            
            logger.info(f"Bulk releasing: {len(ordered_items or [])} ordered items, {len(consumptions or [])} consumptions")
            
            response = await send_post_request(
                endpoint=endpoint,
                json_data=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                return parsed_response
            else:
                status_code = getattr(response, 'status_code', 500)
                logger.error(f"Bulk release failed: {parsed_response}")
                raise Exception(f"Bulk release failed: {parsed_response}")
                
        except Exception as e:
            logger.error(f"Failed to bulk release: {e}")
            raise
    
    async def health_check(self) -> Dict[str, str]:
        """Check the health of the Inventory API."""
        try:
            endpoint = f"{self.base_url}/inventory/health"
            
            response = await send_get_request(
                endpoint=endpoint,
                params={}
            )
            
            parsed_response = self._parse_response(response)
            
            if hasattr(response, 'status_code') and response.status_code == 200:
                return parsed_response
            else:
                return {"status": "unhealthy", "error": str(parsed_response)}
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}