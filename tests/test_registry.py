"""Tests for the Skill Registry."""

import pytest
from backend.core.registry import skill_registry
from backend.core.errors import SkillNotFoundError


class TestSkillRegistry:
    def test_discover_and_load(self):
        skills = skill_registry.discover_and_load()
        assert len(skills) > 0
        assert "apps" in skills
        assert "chat" in skills
        assert "timers" in skills

    def test_get_existing_skill(self):
        skill = skill_registry.get("apps")
        assert skill.name == "apps"
        assert skill.enabled is True

    def test_get_nonexistent_skill(self):
        with pytest.raises(SkillNotFoundError):
            skill_registry.get("nonexistent_skill")

    def test_list_skills(self):
        skills = skill_registry.list_skills()
        assert len(skills) > 0
        assert any(s["name"] == "apps" for s in skills)

    def test_get_manifest(self):
        manifest = skill_registry.get_manifest("apps")
        assert manifest["name"] == "apps"
        assert "actions" in manifest

    def test_find_handler(self):
        skill = skill_registry.find_handler("apps", "open")
        assert skill.name == "apps"

    def test_get_risk(self):
        risk = skill_registry.get_risk("apps", "open")
        assert risk.value == "safe"
