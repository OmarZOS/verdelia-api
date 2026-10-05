# wiring/domain_counters.py
"""
Register domain counters on the DomainLimitService.

Each counter answers "how many of X exist at scope Y?". The scope
depends on the resource:

    organization_owned       scope = user id
    provider_owned           scope = user id
    team_members             scope = user id  (sums across orgs)
    products_per_provider    scope = provider id
    services_per_provider    scope = provider id

Each counter delegates to `storage_broker.count(...)`, which is the
same query path the rest of the codebase uses. This keeps the wiring
layer free of direct SQLAlchemy imports — no `Session`, no `select`,
no `func.count`. Just the broker's `count(table, conditions)` call.

No session is threaded through. The broker owns its own connection
management (engine + sessionmaker per call). Registering once at
startup is enough.
"""

from core.models.app_models import ResourceCode
from core.models.models import (
    ManagementRule,
    Product,
    ProductProvider,
    ProvidedService,
    ProviderOrganisation,
)
from services.domain_limit_service import DomainLimitService
import storage.storage_broker as storage_broker


def wire_domain_counters(service: DomainLimitService) -> None:
    """Attach per-resource counters that use the storage broker."""

    service.register_counter(
        ResourceCode.ORGANIZATION_OWNED,
        lambda user_id: storage_broker.count(
            ProviderOrganisation,
            {ProviderOrganisation.app_user_id: user_id},
        ),
    )

    service.register_counter(
        ResourceCode.PROVIDER_OWNED,
        lambda user_id: storage_broker.count(
            ProductProvider,
            {ProductProvider.product_provider_owner: user_id},
        ),
    )

    service.register_counter(
        ResourceCode.TEAM_MEMBERS,
        lambda user_id: _count_team_members(user_id),
    )

    service.register_counter(
        ResourceCode.PRODUCTS_PER_PROVIDER,
        lambda provider_id: storage_broker.count(
            Product,
            {Product.product_provider_id: provider_id},
        ),
    )

    service.register_counter(
        ResourceCode.SERVICES_PER_PROVIDER,
        lambda provider_id: storage_broker.count(
            ProvidedService,
            {
                ProvidedService.provided_service_product_provider_id:
                    provider_id
            },
        ),
    )


def _count_team_members(user_id: int) -> int:
    """Count every management rule tied to an organisation owned by
    the user.

    The broker's `count()` takes equality conditions only, so the
    join to `ProviderOrganisation` can't be expressed in a single
    call. Two options:

    1. Fetch the user's org ids, then count rules whose
       `rule_ref_org` is in that list. That's `count()` per org,
       summed.
    2. Fetch the user's org ids, then fetch all rules, filter in
       Python.

    Option 1 is used here — it stays in the broker's vocabulary and
    the org count is bounded (a user rarely has more than a few).
    """
    orgs = storage_broker.get(
        ProviderOrganisation,
        {ProviderOrganisation.app_user_id: user_id},
        None,
        [],
    )
    if not orgs:
        return 0

    total = 0
    for org in orgs:
        total += storage_broker.count(
            ManagementRule,
            {ManagementRule.rule_ref_org: org.idprovider_organisation},
        )
    return total