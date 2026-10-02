# storage/seeds/_naming.py

"""Shared helpers for the seed modules that use NamingContribution."""

from typing import Any, Optional

from storage.storage_broker import get, insert_record
from core.models import models


def first(result: Any) -> Optional[Any]:
    """
    Normalise a `storage_broker` result to a single row.

    `get()` and `insert_record()` return lists; the seed code wants
    scalars. This is the one place that knows that.
    """
    if result is None:
        return None
    if isinstance(result, list):
        return result[0] if result else None
    return result


def get_or_create_naming_contribution(
    *,
    name_en: str,
    name_ar: str,
    name_fr: str,
    contribution_type: str,
    icon_url: Optional[str] = None,
) -> Optional[Any]:
    """
    Return the existing NamingContribution for the given English name,
    or insert a new one.

    Idempotent: re-running with the same `name_en` returns the existing
    row rather than inserting a duplicate.
    """
    existing = first(
        get(
            table=models.NamingContribution,
            conditions={"naming_contribution_en": name_en},
        )
    )
    if existing:
        return existing

    contribution = models.NamingContribution(
        naming_contribution_en=name_en,
        naming_contribution_ar=name_ar,
        naming_contribution_fr=name_fr,
        naming_contribution_status="APP_TRANSLATED",
        naming_contribution_type=contribution_type,
        naming_contribution_icon_url=icon_url,
        naming_contribution_by=None,
        naming_contribution_app_version=None,
    )
    return first(insert_record(contribution))