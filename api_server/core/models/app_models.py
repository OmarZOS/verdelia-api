# core/models/app_models.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


# ══════════════════════════════════════════════════════════════════
# Resources
# ══════════════════════════════════════════════════════════════════


class ResourceKind(str, Enum):
    """How a resource's limit value should be interpreted.

    Distinct from `LimitKind`: `ResourceKind` describes *what the
    resource measures* (a count, a flag, a byte size). `LimitKind`
    describes *what a particular plan says about the resource*
    (disabled, unlimited, negotiated, finite).
    """

    QUOTA = "quota"
    """A countable ceiling. `0` = none, `>0` = cap, `-1` = unlimited,
    `-2` = negotiated."""

    FLAG = "flag"
    """A boolean toggle. `0` = disabled, non-zero = enabled.
    Sentinels are meaningless and should be treated as errors."""

    BYTES = "bytes"
    """A quota measured in bytes. Same sentinel semantics as QUOTA,
    but the UI and messages format the number differently."""


class CountingStrategy(str, Enum):
    """Where a resource's *current count* comes from.

    Distinct from `ResourceKind`, which describes what the limit
    measures. `ResourceKind` answers "what does the number mean?"
    `CountingStrategy` answers "where do I read the number from?"

    A resource needs both axes:

        AI_CREDITS_MONTHLY   kind=QUOTA   counting=PERIOD
        PROVIDER_OWNED       kind=QUOTA   counting=DOMAIN
        ADS_ENABLED          kind=FLAG    counting=FLAG
    """

    PERIOD = "period"
    """Counted in `subscription_usage`. Resets each billing period.
    Check with `UsageService`."""

    DOMAIN = "domain"
    """Counted from a domain table (`SELECT COUNT(*) ...`). Never
    resets. Check with `DomainLimitService`, supplying the count."""

    FLAG = "flag"
    """Not counted. The limit value *is* the state. Read the
    `plan_limit` row directly; there's no count to compare."""



class ResourceCode(str, Enum):
    """Canonical resource codes used in `plan_limit.resource_code`.

    Inherits from `str` so instances compare equal to their string
    value: `ResourceCode.PROVIDER_OWNED == "provider_owned"` is True,
    which means existing code paths that pass strings keep working
    during a migration.
    """

    ORGANIZATION_OWNED = "organization_owned"
    PROVIDER_OWNED = "provider_owned"
    TEAM_MEMBERS = "team_members"
    PRODUCTS_PER_PROVIDER = "products_per_provider"
    SERVICES_PER_PROVIDER = "services_per_provider"
    AI_CREDITS_MONTHLY = "ai_credits_monthly"
    ADS_ENABLED = "ads_enabled"

    @property
    def counting(self) -> CountingStrategy:
        """Where this resource's current count comes from."""
        return _RESOURCE_COUNTING[self.value]

    @classmethod
    def from_wire(cls, value: str) -> "ResourceCode | None":
        """Parse a wire value. Returns None for unknown codes rather
        than raising — a plan row with an unrecognised resource is a
        forward-compatibility problem, not a crash."""
        try:
            return cls(value)
        except ValueError:
            return None

    @property
    def kind(self) -> ResourceKind:
        """How this resource's limit value should be interpreted."""
        return _RESOURCE_KINDS[self.value]

    @property
    def description(self) -> str:
        """Human-readable description. Used for logs and admin
        tooling, not the user-facing UI (which has localized strings
        on the app side)."""
        return _RESOURCE_DESCRIPTIONS[self.value]


# Keyed by wire value (str), not by enum member. This lets the maps
# be defined below the class without a forward reference, and makes
# the "typed view over strings" relationship explicit.
_RESOURCE_KINDS: Final[dict[str, ResourceKind]] = {
    "organization_owned": ResourceKind.QUOTA,
    "provider_owned": ResourceKind.QUOTA,
    "team_members": ResourceKind.QUOTA,
    "products_per_provider": ResourceKind.QUOTA,
    "services_per_provider": ResourceKind.QUOTA,

    "ai_credits_monthly": ResourceKind.QUOTA,
    "ads_enabled": ResourceKind.FLAG,
}

_RESOURCE_COUNTING: Final[dict[str, CountingStrategy]] = {
    "organization_owned": CountingStrategy.DOMAIN,
    "provider_owned": CountingStrategy.DOMAIN,
    "team_members": CountingStrategy.DOMAIN,
    "products_per_provider": CountingStrategy.DOMAIN,
    "services_per_provider": CountingStrategy.DOMAIN,
    "ai_credits_monthly": CountingStrategy.PERIOD,
    "ads_enabled": CountingStrategy.FLAG,
}

_RESOURCE_DESCRIPTIONS: Final[dict[str, str]] = {
    "organization_owned": "Organizations the user can create",
    "provider_owned": "Suppliers the user can create",
    "team_members": "Members the user can invite",
    "products_per_provider": "Products per supplier",
    "services_per_provider": "Services per supplier",
    "ai_credits_monthly": "Monthly AI credits",     # ← add this
    "ads_enabled": "Whether the plan shows ads",
}



# ══════════════════════════════════════════════════════════════════
# Limits
# ══════════════════════════════════════════════════════════════════
#
# `plan_limit.limit_value` uses four distinct encodings:
#
#     > 0   a hard numeric ceiling
#     0     the resource is not available on this plan
#     -1    unlimited by design (internal use; never a flat-price plan)
#     -2    negotiated per contract (Enterprise only)
#
# `-1` and `-2` are not interchangeable. Code that treats any
# negative value as "unlimited" will mis-handle Enterprise.

UNLIMITED: Final[int] = -1
NEGOTIATED: Final[int] = -2
DISABLED: Final[int] = 0


class LimitKind(str, Enum):
    """The interpretation of a single limit value.

    Distinct from `ResourceKind`: `ResourceKind` describes *what the
    resource measures* (quota, flag, bytes), `LimitKind` describes
    *what this particular plan row says about that resource*
    (disabled, unlimited, negotiated, finite).
    """

    DISABLED = "disabled"       # value == 0
    UNLIMITED = "unlimited"     # value == -1
    NEGOTIATED = "negotiated"   # value == -2
    FINITE = "finite"           # value > 0
    UNKNOWN = "unknown"         # anything else (bad data)


@dataclass(frozen=True)
class Limit:
    """A single resource's limit, resolved from a `PlanLimit` row.

    `value` is preserved verbatim so callers can round-trip it. Use
    `kind` to branch, not `value`.
    """

    resource: ResourceCode
    value: int

    @property
    def kind(self) -> LimitKind:
        if self.value == DISABLED:
            return LimitKind.DISABLED
        if self.value == UNLIMITED:
            return LimitKind.UNLIMITED
        if self.value == NEGOTIATED:
            return LimitKind.NEGOTIATED
        if self.value > 0:
            return LimitKind.FINITE
        return LimitKind.UNKNOWN

    # ── Predicates ─────────────────────────────────────────────

    @property
    def is_disabled(self) -> bool:
        """The resource is not available on this plan."""
        return self.kind is LimitKind.DISABLED

    @property
    def is_unlimited(self) -> bool:
        """No cap, by design."""
        return self.kind is LimitKind.UNLIMITED

    @property
    def is_negotiated(self) -> bool:
        """Cap defined by contract, not by this row."""
        return self.kind is LimitKind.NEGOTIATED

    @property
    def is_finite(self) -> bool:
        """A concrete numeric ceiling."""
        return self.kind is LimitKind.FINITE

    @property
    def is_capped(self) -> bool:
        """True when a hard ceiling applies — either a number, or the
        absence of the resource entirely.

        Negotiated and unlimited are *not* capped at this layer.
        Callers that need to enforce negotiated caps must consult the
        contract separately.
        """
        return self.kind in (LimitKind.FINITE, LimitKind.DISABLED)

    @property
    def ceiling(self) -> int | None:
        """The numeric ceiling, or None when there isn't one at this
        layer.

        Disabled resources have a ceiling of `0` for arithmetic
        purposes, but callers who care about that case should check
        `is_disabled` first.
        """
        if self.kind is LimitKind.FINITE:
            return self.value
        if self.kind is LimitKind.DISABLED:
            return 0
        return None


@dataclass(frozen=True)
class LimitCheck:
    """The result of checking an operation against a plan limit."""

    allowed: bool
    resource: ResourceCode
    limit: Limit
    current: int
    requested: int
    reason: str

    @property
    def remaining(self) -> int | None:
        """Headroom right now — how many more can be created
        *before* the next operation.

        This is `ceiling - current`, not `ceiling - current -
        requested`. The `requested` amount is what the caller is
        *checking*, not what they've already done. A summary that
        says "1 of 500 used, 499 remaining" is describing the
        state right now; subtracting the imaginary next request
        would make it "498 remaining" before the user did anything.
        """
        ceiling = self.limit.ceiling
        if ceiling is None:
            return None
        return max(0, ceiling - self.current)


def check_limit(
    limits: dict[ResourceCode, Limit],
    resource: ResourceCode,
    current_count: int,
    requested: int = 1,
) -> LimitCheck:
    """Check whether creating `requested` more of `resource` is allowed.

    `current_count` is the number the user has *now*, not including
    the operation being checked. For a create, `current_count` is
    what exists; for a bulk create of N, `requested` is N.

    Returns a `LimitCheck`. Never raises — a missing resource is
    treated as denied, because a plan that doesn't define a resource
    can't grant it.
    """
    limit = limits.get(resource)
    if limit is None:
        # The plan didn't define this resource. Deny by default:
        # a plan can only grant what it explicitly lists.
        return LimitCheck(
            allowed=False,
            resource=resource,
            limit=Limit(resource=resource, value=DISABLED),
            current=current_count,
            requested=requested,
            reason=f"Plan does not define resource {resource.value!r}",
        )

    if current_count < 0:
        return LimitCheck(
            allowed=False,
            resource=resource,
            limit=limit,
            current=current_count,
            requested=requested,
            reason="current_count must be non-negative",
        )

    if requested <= 0:
        # A zero-or-negative request is a no-op; allow it so callers
        # don't have to special-case "check, then maybe act".
        return LimitCheck(
            allowed=True,
            resource=resource,
            limit=limit,
            current=current_count,
            requested=requested,
            reason="no-op request",
        )

    match limit.kind:
        case LimitKind.DISABLED:
            return LimitCheck(
                allowed=False,
                resource=resource,
                limit=limit,
                current=current_count,
                requested=requested,
                reason="Resource is not available on this plan",
            )

        case LimitKind.UNLIMITED:
            return LimitCheck(
                allowed=True,
                resource=resource,
                limit=limit,
                current=current_count,
                requested=requested,
                reason="unlimited",
            )

        case LimitKind.NEGOTIATED:
            # The plan row can't answer this. Allow at this layer;
            # the caller is responsible for consulting the contract.
            return LimitCheck(
                allowed=True,
                resource=resource,
                limit=limit,
                current=current_count,
                requested=requested,
                reason="negotiated; contract check required",
            )

        case LimitKind.FINITE:
            # `kind is FINITE` implies `value > 0`, so `value` is the
            # ceiling. No need to route through `.ceiling`, which
            # returns `int | None`.
            ceiling = limit.value
            allowed = (current_count + requested) <= ceiling
            reason = (
                "within limit"
                if allowed
                else f"would exceed limit of {ceiling} "
                     f"({current_count} + {requested})"
            )
            return LimitCheck(
                allowed=allowed,
                resource=resource,
                limit=limit,
                current=current_count,
                requested=requested,
                reason=reason,
            )

        case LimitKind.UNKNOWN:
            # Bad data — the row's value is neither 0, -1, -2, nor
            # positive. Deny and log loudly elsewhere.
            return LimitCheck(
                allowed=False,
                resource=resource,
                limit=limit,
                current=current_count,
                requested=requested,
                reason=f"Unknown limit value {limit.value}",
            )

    # Unreachable — the match above is exhaustive over LimitKind.
    raise AssertionError(f"unhandled limit kind: {limit.kind}")


def resolve_limits(plan) -> dict[ResourceCode, Limit]:
    """Build the resource→limit map for a `Plan` ORM instance.

    Unknown resource codes on the row are skipped, not raised. This
    lets a plan carry forward-compatible limit rows that an older
    version of the app doesn't understand yet.

    A resource that appears twice on the same plan: the last row
    wins. That shouldn't happen — the database should enforce a
    unique index on `(plan_id, resource_code)` — but if it does,
    silently taking the last value is better than raising during a
    request.

    A plan with no related `plan_limit` rows, or with a partially
    loaded/None relation, resolves to an empty map rather than
    crashing the request path. That yields the safe default of
    "resource not defined on this plan" during checks.
    """
    if plan is None:
        return {}

    rows = getattr(plan, "plan_limit", None) or []
    resolved: dict[ResourceCode, Limit] = {}
    for row in rows:
        resource_code = getattr(row, "resource_code", None)
        if resource_code is None:
            continue

        resource = ResourceCode.from_wire(resource_code)
        if resource is None:
            continue

        limit_value = getattr(row, "limit_value", 0)
        resolved[resource] = Limit(resource=resource, value=limit_value)
    return resolved