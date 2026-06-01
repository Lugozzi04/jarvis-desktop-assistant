"""Tests for the Permission Guard."""

import pytest
from backend.core.permissions import permission_guard
from backend.core.schemas import RiskLevel


class TestPermissionGuard:
    def test_safe_auto_approved(self):
        result = permission_guard.check(RiskLevel.safe, "Open Discord")
        assert result["allowed"] is True
        assert result["needs_confirmation"] is False

    def test_confirmation_required(self):
        result = permission_guard.check(RiskLevel.confirmation, "Close Discord")
        assert result["allowed"] is True
        assert result["needs_confirmation"] is True

    def test_dangerous_strong_confirm(self):
        result = permission_guard.check(RiskLevel.dangerous, "Delete all files")
        assert result["allowed"] is True
        assert result["needs_confirmation"] is True
        assert "CONFIRM" in result["confirmation_message"].upper()
