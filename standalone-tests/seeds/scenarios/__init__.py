# test_runner/scenarios/__init__.py
"""Per-router scenario modules.

Each module owns one API surface. `TestRunner` in `runner.py`
constructs one instance per module and delegates to them.
"""

from .organisations import OrganisationsScenario
from .products import ProductsScenario
from .services import ServicesScenario
from .staff import StaffScenario
from .subscriptions import SubscriptionsScenario
from .suppliers import SuppliersScenario
from .cart import CartScenario
from .users import UsersScenario
from .usage import UsageScenario
from .wallet import WalletScenario

__all__ = [
    "OrganisationsScenario",
    "ProductsScenario",
    "ServicesScenario",
    "StaffScenario",
    "CartScenario",
    "WalletScenario",
    "SubscriptionsScenario",
    "SuppliersScenario",
    "UsersScenario",
    "UsageScenario"
]