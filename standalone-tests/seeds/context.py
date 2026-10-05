# test_runner/context.py
"""Persisted test state and volume profiles.

TestUser / TestContext are what allow a run to be interrupted and
resumed. VolumeProfile is what lets the runner scale between smoke
tests and load-shape tests without editing the runner.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TestUser:
    id: int = 0
    username: str = ""
    email: str = ""
    password: str = ""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    user_data: Dict[str, Any] = field(default_factory=dict)
    person_data: Dict[str, Any] = field(default_factory=dict)
    location_data: Dict[str, Any] = field(default_factory=dict)
    roles: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expires_at": (
                self.token_expires_at.isoformat()
                if self.token_expires_at else None
            ),
            "user_data": self.user_data,
            "person_data": self.person_data,
            "location_data": self.location_data,
            "roles": self.roles,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestUser":
        expires_at = data.get("token_expires_at")
        return cls(
            id=data.get("id", 0),
            username=data.get("username", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_expires_at=(
                datetime.fromisoformat(expires_at) if expires_at else None
            ),
            user_data=data.get("user_data", {}),
            person_data=data.get("person_data", {}),
            location_data=data.get("location_data", {}),
            roles=data.get("roles", []),
        )


@dataclass
class TestContext:
    users: List[TestUser] = field(default_factory=list)
    created_organisations: List[int] = field(default_factory=list)
    created_suppliers: List[int] = field(default_factory=list)
    created_products: List[int] = field(default_factory=list)
    created_services: List[int] = field(default_factory=list)
    created_staff_rules: List[int] = field(default_factory=list)
    created_subscriptions: List[int] = field(default_factory=list)
    user_org_mapping: Dict[int, List[int]] = field(default_factory=dict)
    user_supplier_mapping: Dict[int, List[int]] = field(default_factory=dict)
    user_roles: Dict[int, List[str]] = field(default_factory=dict)
    subscription_user_mapping: Dict[int, List[int]] = field(
        default_factory=dict
    )

    def save(self, filename: str = "test_context.json") -> None:
        data = {
            "users": [u.to_dict() for u in self.users],
            "created_organisations": self.created_organisations,
            "created_suppliers": self.created_suppliers,
            "created_products": self.created_products,
            "created_services": self.created_services,
            "created_staff_rules": self.created_staff_rules,
            "created_subscriptions": self.created_subscriptions,
            "user_org_mapping": self.user_org_mapping,
            "user_supplier_mapping": self.user_supplier_mapping,
            "user_roles": self.user_roles,
            "subscription_user_mapping":
                self.subscription_user_mapping,
            "timestamp": datetime.now().isoformat(),
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Test context saved to {filename}")

    def load(self, filename: str = "test_context.json") -> bool:
        """Load test context from a JSON file.

        Returns True when the file was read and parsed. Returns False
        when the file does not exist. Raises on malformed JSON — a
        corrupt context file is a bug worth surfacing, not silently
        skipping.
        """
        path = Path(filename)
        if not path.exists():
            return False

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Test context file {filename!r} is not valid JSON: {e}"
            ) from e

        if not isinstance(data, dict):
            raise RuntimeError(
                f"Test context file {filename!r} must contain a JSON "
                f"object, got {type(data).__name__}"
            )

        self.users = [TestUser.from_dict(u) for u in data.get("users", [])]
        self.created_organisations = data.get(
            "created_organisations", []
        )
        self.created_suppliers = data.get("created_suppliers", [])
        self.created_products = data.get("created_products", [])
        self.created_services = data.get("created_services", [])
        self.created_staff_rules = data.get("created_staff_rules", [])
        self.created_subscriptions = data.get(
            "created_subscriptions", []
        )
        self.user_org_mapping = data.get("user_org_mapping", {})
        self.user_supplier_mapping = data.get(
            "user_supplier_mapping", {}
        )
        self.user_roles = data.get("user_roles", {})
        self.subscription_user_mapping = data.get(
            "subscription_user_mapping", {}
        )
        print(f"📂 Test context loaded from {filename}")
        return True


@dataclass(frozen=True)
class VolumeProfile:
    """How much data to generate per run."""
    name: str
    users: int
    orgs_per_user: int
    suppliers_per_org: int
    products_per_supplier: int
    services_per_supplier: int
    staff_rules_per_supplier: int


SMOKE = VolumeProfile(
    name="smoke",
    users=10,
    orgs_per_user=3,
    suppliers_per_org=3,
    products_per_supplier=5,
    services_per_supplier=2,
    staff_rules_per_supplier=2,
)

STANDARD = VolumeProfile(
    name="standard",
    users=50,
    orgs_per_user=2,
    suppliers_per_org=5,
    products_per_supplier=20,
    services_per_supplier=5,
    staff_rules_per_supplier=3,
)

STRESS = VolumeProfile(
    name="stress",
    users=200,
    orgs_per_user=3,
    suppliers_per_org=10,
    products_per_supplier=50,
    services_per_supplier=20,
    staff_rules_per_supplier=5,
)

PROFILES = {
    "smoke": SMOKE,
    "standard": STANDARD,
    "stress": STRESS,
}