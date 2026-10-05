from types import SimpleNamespace

import pytest

from core.models.api_models import Product_API
from core.models.app_models import (
    Limit,
    LimitCheck,
    ResourceCode,
    resolve_limits,
)
from workflows.product_workflow import ProductWorkflow


def test_resolve_limits_handles_missing_plan_limits() -> None:
    plan = SimpleNamespace(plan_limit=None)

    assert resolve_limits(plan) == {}


def test_resolve_limits_skips_unknown_resource_codes() -> None:
    plan = SimpleNamespace(
        plan_limit=[
            SimpleNamespace(resource_code="unknown_resource", limit_value=99),
            SimpleNamespace(resource_code="ai_credits_monthly", limit_value=12),
        ]
    )

    limits = resolve_limits(plan)

    assert limits[ResourceCode.AI_CREDITS_MONTHLY].value == 12
    assert ResourceCode.AI_CREDITS_MONTHLY in limits


def test_product_create_enforces_provider_limit_from_user_subscription() -> None:
    class FakeDomainLimits:
        def __init__(self):
            self.calls = []

        def check_with_count(
            self,
            subscription_id,
            resource,
            current_count,
            requested=1,
        ):
            self.calls.append(
                {
                    "subscription_id": subscription_id,
                    "resource": resource,
                    "current_count": current_count,
                    "requested": requested,
                }
            )
            return SimpleNamespace(
                allowed=True,
                check=LimitCheck(
                    allowed=True,
                    resource=resource,
                    limit=Limit(resource=resource, value=10),
                    current=current_count,
                    requested=requested,
                    reason="within limit",
                ),
            )

        def ceiling(self, subscription_id, resource):
            return 10

    class FakeSubscriptionService:
        def get_subscription_for_user(self, user_id):
            return SimpleNamespace(id_subscription=42)

    class FakeProductService:
        def count_products_for_provider(self, provider_id):
            assert provider_id == 7
            return 9

        def create_product(self, **kwargs):
            return SimpleNamespace(id_product=99)

        def delete_product(self, product_id, force_delete):
            return True

    workflow = ProductWorkflow(
        service=FakeProductService(),
        subscription_service=FakeSubscriptionService(),
        domain_limits=FakeDomainLimits(),
        ai_service=None,
        usage_service=None,
    )

    product = Product_API(product_name="Test product", product_provider_id=7)

    result = __import__("asyncio").run(
        workflow.create_product(product, user_id=1)
    )

    assert result.id_product == 99
    assert workflow.domain_limits.calls[0]["subscription_id"] == 42
    assert workflow.domain_limits.calls[0]["current_count"] == 9
    assert workflow.domain_limits.calls[0]["resource"] == ResourceCode.PRODUCTS_PER_PROVIDER


def test_product_create_rejects_missing_subscription_context() -> None:
    workflow = ProductWorkflow(
        service=SimpleNamespace(),
        subscription_service=SimpleNamespace(),
        domain_limits=SimpleNamespace(),
        ai_service=None,
        usage_service=None,
    )

    product = Product_API(
        product_name="Test product",
        product_provider_id=7,
    )

    with pytest.raises(ValueError, match="requires user_id or subscription_id"):
        __import__("asyncio").run(workflow.create_product(product))


def test_product_create_rejects_over_limit_provider_count() -> None:
    class FakeDomainLimits:
        def check_with_count(self, subscription_id, resource, current_count, requested=1):
            return SimpleNamespace(
                allowed=False,
                check=LimitCheck(
                    allowed=False,
                    resource=resource,
                    limit=Limit(resource=resource, value=5),
                    current=current_count,
                    requested=requested,
                    reason="would exceed limit of 5",
                ),
            )

        def ceiling(self, subscription_id, resource):
            return 5

    class FakeSubscriptionService:
        def get_subscription_for_user(self, user_id):
            return SimpleNamespace(id_subscription=42)

    class FakeProductService:
        def count_products_for_provider(self, provider_id):
            return 5

        def create_product(self, **kwargs):
            return SimpleNamespace(id_product=99)

        def delete_product(self, product_id, force_delete):
            return True

    workflow = ProductWorkflow(
        service=FakeProductService(),
        subscription_service=FakeSubscriptionService(),
        domain_limits=FakeDomainLimits(),
        ai_service=None,
        usage_service=None,
    )

    product = Product_API(product_name="Test product", product_provider_id=7)

    with pytest.raises(Exception):
        __import__("asyncio").run(workflow.create_product(product, user_id=1))
