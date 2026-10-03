# services/naming_flow.py
"""
Resolve-or-create flow for NamingContribution rows.

Every service that persists an entity with a trilingual name follows
the same four steps:

  1. Pick the naming source: nested `naming` block, else flat name,
     else skip.
  2. Look up an existing contribution by English name, or insert one.
  3. Hand the contribution's id to the entity writer.
  4. If the writer raises and step 2 created a fresh contribution,
     delete it so retries don't leave orphans.

This module owns all four. Callers get back a tiny value object —
`ResolvedNaming` — that carries only the id and a was_created flag.
The ORM instance itself never crosses the module boundary, which
sidesteps the cross-session bug that bit ProductService.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Protocol

from repositories.naming_contribution_repository import (
    NamingContributionRepository,
)

from core.logging_config import get_logger

logger = get_logger(__name__)



@dataclass(frozen=True)
class ResolvedNaming:
    """Outcome of a resolve-or-create call."""

    id: Optional[int]
    """The contribution's primary key, or None when nothing was
    resolved (no name supplied)."""

    was_created: bool
    """True when this call inserted the row. False when the row
    already existed or when nothing was resolved."""

    @property
    def is_usable(self) -> bool:
        return self.id is not None


class NamingPayload(Protocol):
    """
    Structural type for anything that carries a `naming` block and a
    flat name fallback. Both `Iproduct_API` and the supplier /
    organisation API models satisfy this.
    """

    naming: Optional[object]
    def name_for_naming(self) -> str:  # pragma: no cover - structural
        ...


class NamingFlow:
    """
    Resolve-or-create a NamingContribution, with optional rollback.

    Usage in a service method:

        flow = NamingFlow(self.naming_repo, "provider")
        resolved = flow.resolve(payload.naming, payload.provider_name)

        try:
            entity = self.delegate.create(
                ..., naming_contribution_id=resolved.id,
            )
        except Exception:
            flow.rollback(resolved, "supplier create")
            raise

    Or with the context manager, which does the same thing but reads
    more cleanly:

        with flow.for_payload(naming=payload.naming,
                              fallback=payload.provider_name) as resolved:
            entity = self.delegate.create(
                ..., naming_contribution_id=resolved.id,
            )
    """

    def __init__(
        self,
        naming_repo: NamingContributionRepository,
        contribution_type: str,
        *,
        default_status: str = "APP_TRANSLATED",
    ) -> None:
        self._repo = naming_repo
        self._type = contribution_type
        self._default_status = default_status

    # ==================== Public API ====================

    def resolve(
        self,
        naming: Optional[object],
        fallback_name: Optional[str],
    ) -> ResolvedNaming:
        """
        Return the id of a NamingContribution for this payload, or an
        empty ResolvedNaming when there is no name to work with.

        `naming` is the optional nested block; `fallback_name` is the
        flat name to synthesise from when the nested block is absent.
        """
        nested_name_en = self._nested_english(naming)

        if nested_name_en is not None:
            return self._resolve_from_nested(naming, nested_name_en)

        flat = (fallback_name or "").strip()
        if not flat:
            return ResolvedNaming(id=None, was_created=False)

        return self._resolve_from_flat(flat)

    def rollback(self, resolved: ResolvedNaming, context: str) -> None:
        """
        Delete the contribution iff this flow created it. Best effort:
        logs and swallows any failure, because the caller's original
        exception is more important than a failed cleanup.
        """
        if resolved is None or not resolved.is_usable:
            return
        if not resolved.was_created:
            return

        try:
            self._repo.delete(resolved.id)
            logger.warning(
                "Rolled back NamingContribution %s after %s failed",
                resolved.id,
                context,
            )
        except Exception as rollback_err:
            logger.error(
                "Failed to roll back NamingContribution %s: %s",
                resolved.id,
                rollback_err,
            )

    # ==================== Context manager ====================

    class _Session:
        def __init__(
            self,
            flow: "NamingFlow",
            naming: Optional[object],
            fallback: Optional[str],
            context: str,
        ) -> None:
            self._flow = flow
            self._naming = naming
            self._fallback = fallback
            self._context = context
            self.resolved: Optional[ResolvedNaming] = None

        def __enter__(self) -> ResolvedNaming:
            self.resolved = self._flow.resolve(self._naming, self._fallback)
            return self.resolved

        def __exit__(self, exc_type, exc, tb) -> bool:
            if exc_type is not None and self.resolved is not None:
                self._flow.rollback(self.resolved, self._context)
            # Never suppress the exception.
            return False

    def for_payload(
        self,
        *,
        naming: Optional[object],
        fallback: Optional[str],
        context: str = "entity write",
    ) -> "_Session":
        """
        Context-manager form. On a clean exit, nothing is rolled back.
        On an exception inside the block, a freshly-created
        contribution is deleted and the exception propagates.
        """
        return NamingFlow._Session(self, naming, fallback, context)

    # ==================== Internals ====================

    @staticmethod
    def _nested_english(naming: Optional[object]) -> Optional[str]:
        """
        Return `naming.en` when the nested block is present and its
        English value is non-empty. Otherwise None. Supports both the
        Pydantic API model (`.en` attribute) and a plain dict
        (`naming["en"]`), so the flow works whether the caller passes
        an API model or a raw payload.
        """
        if naming is None:
            return None

        # Pydantic / object form
        en = getattr(naming, "en", None)
        if en is None and isinstance(naming, dict):
            en = naming.get("en")

        if en is None:
            return None

        en = str(en).strip()
        return en or None

    def _resolve_from_nested(
        self,
        naming: object,
        name_en: str,
    ) -> ResolvedNaming:
        existing = self._repo.get_by_english(
            name_en, contribution_type=self._type
        )
        if existing is not None:
            return ResolvedNaming(
                id=existing.id_naming_contribution,
                was_created=False,
            )

        name_ar = getattr(naming, "ar", None)
        name_fr = getattr(naming, "fr", None)
        icon_url = getattr(naming, "naming_contribution_icon_url", None)
        status = (
            getattr(naming, "naming_contribution_status", None)
            or self._default_status
        )

        # Dict fallback for callers that pass a raw map.
        if isinstance(naming, dict):
            name_ar = name_ar or naming.get("ar")
            name_fr = name_fr or naming.get("fr")
            icon_url = icon_url or naming.get(
                "naming_contribution_icon_url"
            )
            status = status or self._default_status

        contribution = self._repo.get_or_create(
            name_en=name_en,
            name_ar=name_ar,
            name_fr=name_fr,
            contribution_type=self._type,
            icon_url=icon_url,
            status=status,
        )
        return ResolvedNaming(
            id=contribution.id_naming_contribution,
            was_created=True,
        )

    def _resolve_from_flat(self, flat_name: str) -> ResolvedNaming:
        existing = self._repo.get_by_english(
            flat_name, contribution_type=self._type
        )
        if existing is not None:
            return ResolvedNaming(
                id=existing.id_naming_contribution,
                was_created=False,
            )

        contribution = self._repo.get_or_create(
            name_en=flat_name,
            name_ar=flat_name,
            name_fr=flat_name,
            contribution_type=self._type,
        )
        return ResolvedNaming(
            id=contribution.id_naming_contribution,
            was_created=True,
        )