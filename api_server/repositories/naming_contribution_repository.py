# repositories/naming_contribution_repository.py
"""
Repository for NamingContribution rows.

Owns the only writes to `naming_contribution` in the app. The service
layer never constructs the ORM model directly — it calls
`get_or_create` and gets back a persisted row.

Read paths are intentionally thin: lookups by English name (the
natural key used by seeds and the AI pipeline), by primary key, and by
the (English name, type) pair when a caller needs to discriminate
between "product" and "ingredient" that happen to share a name.
"""

import logging
from typing import List, Optional

from core.models.models import NamingContribution
from storage.storage_broker import get, insert_record, session_scope

logger = logging.getLogger(__name__)


class NamingContributionRepository:
    """CRUD for NamingContribution."""

    # ==================== Reads ====================

    def get_by_id(self, contribution_id: int) -> Optional[NamingContribution]:
        if not contribution_id:
            return None
        results = get(
            table=NamingContribution,
            conditions={"id_naming_contribution": contribution_id},
        )
        return self._first(results)

    def get_by_english(
        self,
        name_en: str,
        contribution_type: Optional[str] = None,
    ) -> Optional[NamingContribution]:
        """
        Return the row whose `naming_contribution_en` matches.

        When `contribution_type` is provided, the lookup is scoped to
        that type — useful when the same English string is used as a
        product name and as an ingredient name, and the caller wants
        only one of them.
        """
        if not name_en:
            return None

        conditions = {"naming_contribution_en": name_en}
        if contribution_type:
            conditions["naming_contribution_type"] = contribution_type

        results = get(table=NamingContribution, conditions=conditions)
        return self._first(results)

    def get_by_type(
        self,
        contribution_type: str,
        limit: int = 500,
    ) -> List[NamingContribution]:
        with session_scope() as session:
            return (
                session.query(NamingContribution)
                .filter(
                    NamingContribution.naming_contribution_type
                    == contribution_type
                )
                .limit(limit)
                .all()
            )

    # ==================== Writes ====================

    def get_or_create(
        self,
        *,
        name_en: str,
        name_ar: Optional[str] = None,
        name_fr: Optional[str] = None,
        contribution_type: str = "product",
        icon_url: Optional[str] = None,
        status: str = "APP_TRANSLATED",
    ) -> NamingContribution:
        """
        Return the existing contribution for `name_en` (optionally
        scoped by type), or insert a new one.

        Idempotent: re-running with the same `name_en` and
        `contribution_type` returns the existing row.

        `name_ar` / `name_fr` default to `name_en` when not supplied,
        so the row is never half-empty on the read path.
        """
        if not name_en or not name_en.strip():
            raise ValueError("name_en must not be blank")

        name_en = name_en.strip()

        existing = self.get_by_english(
            name_en, contribution_type=contribution_type
        )
        if existing:
            return existing

        row = NamingContribution(
            naming_contribution_en=name_en,
            naming_contribution_ar=name_ar or name_en,
            naming_contribution_fr=name_fr or name_en,
            naming_contribution_status=status,
            naming_contribution_type=contribution_type,
            naming_contribution_icon_url=icon_url,
            naming_contribution_by=None,
            naming_contribution_app_version=None,
        )

        result = insert_record(row)
        contribution = self._first(result)
        if contribution is None:
            raise RuntimeError(
                f"Failed to insert NamingContribution for {name_en!r}"
            )

        logger.debug(
            "Created NamingContribution %s for %r (%s)",
            contribution.id_naming_contribution,
            name_en,
            contribution_type,
        )
        return contribution

    def update(
        self,
        contribution_id: int,
        *,
        name_en: Optional[str] = None,
        name_ar: Optional[str] = None,
        name_fr: Optional[str] = None,
        icon_url: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[NamingContribution]:
        """
        Update the fields provided. Missing fields are left untouched.

        Returns the updated row, or None if the id doesn't resolve.
        """
        with session_scope() as session:
            row = (
                session.query(NamingContribution)
                .filter(
                    NamingContribution.id_naming_contribution
                    == contribution_id
                )
                .first()
            )
            if not row:
                logger.warning(
                    "NamingContribution %s not found for update",
                    contribution_id,
                )
                return None

            if name_en is not None:
                row.naming_contribution_en = name_en
            if name_ar is not None:
                row.naming_contribution_ar = name_ar
            if name_fr is not None:
                row.naming_contribution_fr = name_fr
            if icon_url is not None:
                row.naming_contribution_icon_url = icon_url
            if status is not None:
                row.naming_contribution_status = status

            session.commit()
            session.refresh(row)
            return row

    def delete(self, contribution_id: int) -> bool:
        """
        Delete the row. Returns True on success, False if not found.

        Callers should ensure no other entity still references the row
        — a foreign key constraint will surface as a DB error here,
        which is the intended behavior.
        """
        with session_scope() as session:
            row = (
                session.query(NamingContribution)
                .filter(
                    NamingContribution.id_naming_contribution
                    == contribution_id
                )
                .first()
            )
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True

    # ==================== Helpers ====================

    @staticmethod
    def _first(result):
        """`storage_broker.get` returns a list; callers want a scalar."""
        if result is None:
            return None
        if isinstance(result, list):
            return result[0] if result else None
        return result