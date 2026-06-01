"""Permission Guard — enforces risk-based access control.

Every action has a risk level: safe, confirmation, or dangerous.
- safe: auto-approved
- confirmation: user must approve via UI
- dangerous: user must provide explicit strong confirmation

Rules are configurable via settings.
"""

from __future__ import annotations

from backend.core.config import settings
from backend.core.logger import audit_log, logger
from backend.core.schemas import RiskLevel


class PermissionGuard:
    """Enforces risk-based permissions for all JARVIS actions."""

    def check(self, risk: RiskLevel, action_description: str) -> dict:
        """Check if an action is allowed.

        Returns:
            dict with:
              - allowed: bool
              - needs_confirmation: bool
              - confirmation_message: str
              - reason: str
        """
        if risk == RiskLevel.safe:
            return {
                "allowed": True,
                "needs_confirmation": False,
                "confirmation_message": "",
                "reason": "Safe action — auto-approved",
            }

        if risk == RiskLevel.confirmation:
            if not settings.security.confirm_dangerous_actions:
                return {
                    "allowed": True,
                    "needs_confirmation": False,
                    "confirmation_message": "",
                    "reason": "Confirmation disabled in settings",
                }
            return {
                "allowed": True,
                "needs_confirmation": True,
                "confirmation_message": (
                    f"⚠️ Confirm: {action_description}\n\n"
                    "Do you want to proceed?"
                ),
                "reason": "Confirmation required",
            }

        if risk == RiskLevel.dangerous:
            return {
                "allowed": True,
                "needs_confirmation": True,
                "confirmation_message": (
                    f"🚨 DANGEROUS ACTION — REQUIRES EXPLICIT CONFIRMATION\n\n"
                    f"Action: {action_description}\n\n"
                    f"To proceed, type: CONFIRM EXECUTE"
                ),
                "reason": "Dangerous action — strong confirmation required",
            }

        return {
            "allowed": False,
            "needs_confirmation": False,
            "confirmation_message": "",
            "reason": f"Unknown risk level: {risk}",
        }

    def log_check(
        self,
        risk: RiskLevel,
        action_desc: str,
        allowed: bool,
        granted: bool | None = None,
    ) -> None:
        """Log a permission check to the audit log."""
        audit_log(
            action=f"permission_check:{action_desc}",
            skill="permission_guard",
            parameters={
                "risk": risk.value,
                "allowed": allowed,
                "granted": granted,
            },
            risk=risk.value,
            result="allowed" if allowed else "denied",
        )


# Singleton
permission_guard = PermissionGuard()
