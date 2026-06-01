"""Tests for the AppSkill execution."""

import pytest
from backend.skills.apps.skill import AppSkill


class TestAppSkill:
    def setup_method(self):
        self.skill = AppSkill()

    def test_open_no_app_name(self):
        result = self.skill.execute("open", {})
        assert result.success is False

    def test_open_unknown_app(self):
        result = self.skill.execute("open", {"app_name": "nonexistent_app_xyz"})
        assert result.success is False

    def test_list_apps(self):
        result = self.skill.execute("list", {})
        assert result.success is True
        assert "Configured apps" in str(result.result)
