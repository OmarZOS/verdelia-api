# workflows/team_workflow.py
"""
Team workflow — orchestration layer for staff assignments.

Owns the sequencing that combines management-rule persistence with
the usage system:

  * `create_rule` checks `TEAM_MEMBERS` before persisting.
  * The count is organisation-scoped: "how many team members does
    this organisation have?" A rule created without an org is not
    counted.

`ManagementRuleService` knows how to persist a rule, how to answer
an invitation, and how to query by user/provider/org. It does not
know that team size is metered. That's this workflow's job.
"""

import logging
from typing import Optional

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
)
from core.models.api_models import ManagementRule_API
from core.models.app_models import ResourceCode
from core.models.models import ManagementRule

from services.domain_limit_service import DomainLimitService
from services.management_rule_service import ManagementRuleService
from services.subscription_service import SubscriptionService

from core.logging_config import get_logger

logger = get_logger(__name__)


class TeamWorkflow:
    """Orchestration around ManagementRuleService."""

    def __init__(
        self,
        rule_service: Optional[ManagementRuleService] = None,
        domain_limits: Optional[DomainLimitService] = None,
        subscription_service: Optional[SubscriptionService] = None,
    ):
        self.service = rule_service or ManagementRuleService()
        self.domain_limits = domain_limits or DomainLimitService()
        self.subscription_service = (
            subscription_service or SubscriptionService()
        )

    # ══════════════════════════════════════════════════════════════
    # Metered create
    # ══════════════════════════════════════════════════════════════

    def create_rule(
        self,
        rule_data: ManagementRule_API,
        *,
        user_id: int,
        subscription_id: Optional[int] = None,
        existing_member_count: Optional[int] = None,
    ) -> ManagementRule:
        """Create a management rule, enforcing the `TEAM_MEMBERS`
        limit.

        The scope is the organisation the rule belongs to. A rule
        with `rule_ref_org` set counts against that org's limit; a
        rule without an org is not metered, because it's not part of
        a team.

        `user_id` is required. Every staff create that changes the
        team roster goes through this method.

        Raises:
            402 RESOURCE_NOT_AVAILABLE when the plan doesn't allow
                team members at all (limit 0).
            429 RESOURCE_LIMIT_EXCEEDED when the org has reached the
                plan's ceiling.
            404 SUBSCRIPTION_NOT_FOUND when the user has no
                subscription.
        """
        org_id = getattr(rule_data, "rule_ref_org", None)
        provider_id = getattr(rule_data, "rule_ref_provider", None)
        invited_user_id = getattr(rule_data, "rule_ref_user", None)

        logger.info(
            f"create_rule: start user_id={user_id} org_id={org_id} "
            f"provider_id={provider_id} invited_user_id={invited_user_id}"
        )

        # Resolve subscription even for unmetered rules — a user
        # with no subscription shouldn't be creating staff rules at
        # all, metered or not.
        subscription_id = self._resolve_subscription(
            user_id=user_id,
            subscription_id=subscription_id,
            operation="create_rule",
        )

        # Rules without an organisation aren't team members. They
        # skip the count but still require a subscription.
        if org_id is None:
            logger.info(
                f"create_rule: rule has no rule_ref_org; skipping "
                f"team-member check"
            )
            return self.service.create_rule(rule_data)

        # ── Domain limit check ─────────────────────────────────
        if existing_member_count is None:
            existing_member_count = (
                self.service.count_team_members_for_org(org_id)
            )
            logger.info(
                f"create_rule: counted existing={existing_member_count} "
                f"members for org_id={org_id}"
            )
        else:
            logger.info(
                f"create_rule: using supplied existing_member_count="
                f"{existing_member_count} for org_id={org_id}"
            )

        result = self.domain_limits.check_with_count(
            subscription_id=subscription_id,
            resource=ResourceCode.TEAM_MEMBERS,
            current_count=existing_member_count,
            requested=1,
        )

        check = result.check
        logger.info(
            f"create_rule: limit check "
            f"resource={check.resource.value} "
            f"current={check.current} requested={check.requested} "
            f"allowed={check.allowed} kind={check.limit.kind.value} "
            f"limit={check.limit.ceiling} remaining={check.remaining} "
            f"reason={check.reason!r}"
        )
        if not result.allowed:
            logger.warning(
                f"create_rule: denying user_id={user_id} "
                f"subscription_id={subscription_id} org_id={org_id} "
                f"resource={check.resource.value} "
                f"current={check.current} "
                f"limit={check.limit.ceiling} "
                f"reason={check.reason!r}"
            )
            raise self._denial_to_exception(check, user_id=user_id)

        # ── Persist ────────────────────────────────────────────
        logger.info(
            f"create_rule: persisting user_id={user_id} org_id={org_id} "
            f"invited_user_id={invited_user_id}"
        )
        try:
            created = self.service.create_rule(rule_data)
        except Exception as e:
            logger.error(
                f"create_rule: persist failed user_id={user_id} "
                f"org_id={org_id}: {e}",
                exc_info=True,
            )
            raise

        logger.info(
            f"create_rule: success user_id={user_id} org_id={org_id} "
            f"rule_id={getattr(created, 'id_management_rule', None)}"
        )
        return created

    def create_rule_unmetered(
        self,
        rule_data: ManagementRule_API,
    ) -> ManagementRule:
        """Create a rule with no plan check.

        For seeders, migrations, and admin bulk imports. Anything
        reachable from an HTTP endpoint must go through `create_rule`.
        """
        return self.service.create_rule(rule_data)

    # ══════════════════════════════════════════════════════════════
    # Unmetered operations — pass through
    # ══════════════════════════════════════════════════════════════
    #
    # Reads, updates, invitation answers, and deletes don't change
    # the team-member count. They go straight to the service.

    def get_rule_by_id(self, rule_id: int) -> ManagementRule:
        return self.service.get_rule_by_id(rule_id)

    def update_rule(
        self, rule_data: ManagementRule_API,
    ) -> ManagementRule:
        return self.service.update_rule(rule_data)

    def answer_invitation(
        self, rule_id: int, accept: bool, user_id: int,
    ) -> ManagementRule:
        return self.service.answer_invitation(rule_id, accept, user_id)

    def delete_rule(
        self, rule_id: int, force_delete: bool = False,
    ):
        return self.service.delete_rule(rule_id, force_delete)

    def get_all_rules(self, **kwargs):
        return self.service.get_all_rules(**kwargs)

    def get_user_rules(self, user_id, status=None):
        return self.service.get_user_rules(user_id, status)

    def get_provider_staff(self, provider_id, active_only=True):
        return self.service.get_provider_staff(provider_id, active_only)

    def get_pending_invitations(self, user_id):
        return self.service.get_pending_invitations(user_id)

    # ══════════════════════════════════════════════════════════════
    # Internals
    # ══════════════════════════════════════════════════════════════

    def _resolve_subscription(
        self,
        *,
        user_id: int,
        subscription_id: Optional[int],
        operation: str,
    ) -> int:
        if subscription_id is not None:
            logger.info(
                f"{operation}: using supplied subscription_id="
                f"{subscription_id} for user_id={user_id}"
            )
            return subscription_id

        sub = self.subscription_service.get_subscription_for_user(user_id)
        if sub is None:
            logger.warning(
                f"{operation}: refusing user_id={user_id} — no "
                f"subscription on file"
            )
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                details={"user_id": user_id},
            )
        logger.info(
            f"{operation}: resolved subscription_id="
            f"{sub.id_subscription} plan_id={sub.subscription_plan_id} "
            f"for user_id={user_id}"
        )
        return sub.id_subscription

    def _denial_to_exception(self, check, *, user_id: int) -> APIException:
        """Translate a failed `LimitCheck` into an API error.

        Mirrors the same method on the other workflows. Duplicated
        rather than imported because the workflows are independent
        layers.
        """
        details = {
            "resource": check.resource.value,
            "current": check.current,
            "requested": check.requested,
            "reason": check.reason,
        }

        if check.limit.is_disabled:
            return APIException(
                status_code=HTTP_402_PAYMENT_REQUIRED,
                error_code=ErrorCode.RESOURCE_NOT_AVAILABLE,
                details=details,
            )

        if check.limit.is_finite:
            details["limit"] = check.limit.ceiling
            details["remaining"] = check.remaining
            return APIException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                details=details,
            )

        logger.error(
            f"Unhandled denial kind for user={user_id}: "
            f"{check.reason}"
        )
        return APIException(
            status_code=HTTP_403_FORBIDDEN,
            error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
            details=details,
        )