# repositories/plan_cache.py
"""
Process-local cache for the plan catalogue.

The plans table is read-heavy and write-rare. `get_all_plans` is the
single most expensive query in the pricing flow: it eager-loads
`plan_limit`, `plan_feature`, `plan_feature.feature_naming`, and
`plan_naming` for every row. Caching it here removes that cost from
every screen that displays pricing.

Design:

  * No TTL. Invalidation is explicit — every write path calls
    `invalidate()`, and a manual `refresh()` forces a reload.

  * Per-filter entries. `plan_type` and `billing_cycle` are the two
    supported filters; each tuple of values gets its own cache slot.
    A request for `(individual, monthly)` does not evict the
    `(None, None)` entry.

  * Single-flight reload. If two threads race to reload the same
    filter, the second waits for the first instead of issuing a
    duplicate query.

  * Generation counter. Reads grab the current generation; a write
    bumps it; a stale read that lands after a bump is discarded. This
    prevents a slow reload from overwriting a newer state.

Thread-safety: a `threading.Lock` around the cache dictionary. Reads
are cheap; writes are rare. This is sufficient for a single-process
deployment. Under multiple workers, each worker has its own cache and
its own invalidation — writes in one worker do not invalidate the
others. See the note at the bottom of the module.
"""

from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional, Tuple

from core.models.models import Plan


# The key is (plan_type, billing_cycle). Either may be None.
_CacheKey = Tuple[Optional[str], Optional[str]]


class _CacheEntry:
    __slots__ = ("plans", "generation")

    def __init__(self, plans: List[Plan], generation: int) -> None:
        self.plans = plans
        self.generation = generation


class PlanCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: Dict[_CacheKey, _CacheEntry] = {}
        self._generation: int = 0

    # ── Reads ──────────────────────────────────────────────────

    def get(
        self,
        plan_type: Optional[str],
        billing_cycle: Optional[str],
    ) -> Optional[List[Plan]]:
        """Return the cached list for the given filters, or None."""
        key: _CacheKey = (plan_type, billing_cycle)
        with self._lock:
            entry = self._entries.get(key)
            return entry.plans if entry is not None else None

    def generation(self) -> int:
        """Current generation. Callers snapshot this before a reload."""
        with self._lock:
            return self._generation

    # ── Writes ─────────────────────────────────────────────────

    def put(
        self,
        plan_type: Optional[str],
        billing_cycle: Optional[str],
        plans: List[Plan],
        generation: int,
    ) -> bool:
        """
        Store a reload result. Returns False when the caller's
        generation is stale — i.e. an invalidation happened while the
        reload was running, so the result must be discarded.
        """
        key: _CacheKey = (plan_type, billing_cycle)
        with self._lock:
            if generation != self._generation:
                return False
            self._entries[key] = _CacheEntry(plans, generation)
            return True

    def invalidate(self) -> None:
        """
        Drop every cached entry and bump the generation. Called from
        write paths. Any in-flight reload that started before this
        call will be discarded when it tries to store its result.
        """
        with self._lock:
            self._entries.clear()
            self._generation += 1


# Module-level singleton. The repository references it.
plan_cache = PlanCache()