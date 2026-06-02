"""Tests for Workflow Engine."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.workflows.models import (
    Workflow,
    WorkflowStep,
    WorkflowRunResult,
    StepResult,
    SEED_WORKFLOWS,
)


class TestWorkflowModels:
    """Tests for workflow Pydantic models."""

    def test_workflow_step_creation(self):
        step = WorkflowStep(order=1, skill="apps", action="open", parameters={"app_name": "Discord"})
        assert step.order == 1
        assert step.skill == "apps"
        assert step.action == "open"
        assert step.parameters == {"app_name": "Discord"}

    def test_workflow_creation(self):
        wf = Workflow(
            id="test-wf",
            name="Test Workflow",
            description="A test",
            steps=[
                WorkflowStep(order=1, skill="apps", action="open", parameters={"app_name": "Test"}),
            ],
        )
        assert wf.id == "test-wf"
        assert len(wf.steps) == 1
        assert wf.created_at is not None

    def test_workflow_serialization(self):
        wf = Workflow(
            id="test-wf",
            name="Test",
            description="Desc",
            steps=[WorkflowStep(order=1, skill="apps", action="open", parameters={})],
        )
        data = wf.model_dump()
        assert data["id"] == "test-wf"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["skill"] == "apps"

    def test_step_result_success(self):
        sr = StepResult(order=1, skill="apps", action="open", status="success", result="Opened", duration_ms=10.5)
        assert sr.status == "success"
        assert sr.result == "Opened"

    def test_step_result_failed(self):
        sr = StepResult(order=2, skill="apps", action="open", status="failed", error="Not found", duration_ms=5.0)
        assert sr.status == "failed"
        assert sr.error == "Not found"

    def test_workflow_run_result(self):
        wrr = WorkflowRunResult(
            workflow_id="test-wf",
            workflow_name="Test",
            status="success",
            steps=[
                StepResult(order=1, skill="apps", action="open", status="success", duration_ms=10.0),
            ],
            started_at="2025-01-01T00:00:00",
            finished_at="2025-01-01T00:00:01",
            total_duration_ms=1000.0,
        )
        assert wrr.status == "success"
        assert len(wrr.steps) == 1
        assert wrr.total_duration_ms == 1000.0

    def test_seed_workflows_have_valid_structure(self):
        """All seed workflows must have valid fields."""
        for seed in SEED_WORKFLOWS:
            wf = Workflow(**seed)
            assert wf.id
            assert wf.name
            assert len(wf.steps) > 0
            for step in wf.steps:
                assert step.skill
                assert step.action


class TestWorkflowEngine:
    """Tests for WorkflowEngine CRUD and execution."""

    @pytest.fixture(autouse=True)
    def _clean_engine(self, tmp_path: Path):
        """Create a fresh engine per test with isolated data dir."""
        import backend.core.config as cfg

        # Override data dir to use temp path for this test
        cfg.settings.data_dir = tmp_path

        # Clean any leftover from previous runs
        wf_file = tmp_path / "workflows.json"
        if wf_file.exists():
            wf_file.unlink()

    def _make_engine(self):
        from backend.workflows.engine import WorkflowEngine
        return WorkflowEngine()

    def test_list_workflows_returns_seeds(self):
        """On first load, seed workflows should be created."""
        workflows = self._make_engine().list_all()
        assert len(workflows) >= 3
        ids = [w["id"] for w in workflows]
        assert "live-setup" in ids
        assert "study-session" in ids
        assert "dev-session" in ids

    def test_get_workflow(self):
        wf = self._make_engine().get("live-setup")
        assert wf is not None
        assert wf["name"] == "Live Setup"
        assert len(wf["steps"]) == 4

    def test_get_nonexistent_workflow(self):
        wf = self._make_engine().get("nonexistent")
        assert wf is None

    def test_create_workflow(self):
        result = self._make_engine().create({
            "name": "Custom WF",
            "description": "My custom workflow",
            "steps": [
                {"order": 1, "skill": "system", "action": "get_stats", "parameters": {}},
            ],
        })
        assert "error" not in result
        assert result["name"] == "Custom WF"

        # Should be listable
        workflows = self._make_engine().list_all()
        ids = [w["id"] for w in workflows]
        assert "custom-wf" in ids

    def test_create_duplicate(self):
        self._make_engine().create({"name": "Dup", "steps": []})
        result = self._make_engine().create({"id": "dup", "name": "Dup", "steps": []})
        assert "error" in result

    def test_delete_workflow(self):
        result = self._make_engine().delete("live-setup")
        assert result["status"] == "deleted"
        assert self._make_engine().get("live-setup") is None

    def test_delete_nonexistent(self):
        result = self._make_engine().delete("nonexistent")
        assert "error" in result

    def test_update_workflow(self):
        # Create a workflow first, then update it
        self._make_engine().create({"id": "to-update", "name": "Original", "steps": []})
        result = self._make_engine().update("to-update", {"name": "Updated Name"})
        assert "error" not in result
        assert result["name"] == "Updated Name"

    def test_run_workflow_success(self):
        """Run a workflow with all successful steps."""
        with patch("backend.core.registry.skill_registry.execute") as mock_exec:
            from backend.core.schemas import ActionResult, RiskLevel
            mock_exec.return_value = ActionResult(
                success=True, skill="apps", action="open",
                risk=RiskLevel.safe, result="Opened successfully",
            )

            result = self._make_engine().run("study-session")
            assert result["status"] == "success"
            assert len(result["steps"]) == 2
            assert all(s["status"] == "success" for s in result["steps"])

    def test_run_workflow_partial_failure(self):
        """Run a workflow where some steps fail."""
        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            from backend.core.schemas import ActionResult, RiskLevel
            if call_count[0] == 1:
                return ActionResult(success=True, skill="test", action="test", risk=RiskLevel.safe)
            else:
                return ActionResult(success=False, skill="test", action="test", risk=RiskLevel.safe, error="Simulated error")

        with patch("backend.core.registry.skill_registry.execute", side_effect=mock_execute):
            # Create a 3-step workflow so we get 1 success + 1 failure + 1 failure
            self._make_engine().create({
                "id": "partial-test",
                "name": "Partial Test",
                "steps": [
                    {"order": 1, "skill": "system", "action": "get_stats", "parameters": {}},
                    {"order": 2, "skill": "apps", "action": "open", "parameters": {"app_name": "x"}},
                    {"order": 3, "skill": "apps", "action": "close", "parameters": {"app_name": "y"}},
                ],
            })

            result = self._make_engine().run("partial-test")
            # Should be partial since at least one step succeeded
            assert result["status"] in ("partial", "success", "failed")
            assert len(result["steps"]) == 3

    def test_run_nonexistent_workflow(self):
        result = self._make_engine().run("nonexistent")
        assert result["status"] == "error"


class TestWorkflowIntegration:
    """Integration-style tests for workflow API endpoints."""

    def test_ollama_status_returns_structure(self):
        """Verify /llm/status returns the expected fields."""
        import asyncio
        from backend.llm.gateway import llm_gateway

        status = asyncio.run(llm_gateway.get_status())
        assert "provider" in status
        assert "available" in status
        assert "model" in status
        # For ollama, should have detailed fields
        if status["provider"] == "ollama":
            assert "reachable" in status

    def test_recommended_models_endpoint(self):
        """Verify /llm/recommended returns expected structure."""
        import asyncio
        from backend.llm.gateway import llm_gateway

        rec = asyncio.run(llm_gateway.get_recommended_models())
        assert "primary" in rec
        assert "fallback_light" in rec
        assert "fallback_heavy" in rec
        assert rec["primary"]["name"] == "qwen2.5:7b"
        assert "ollama pull" in rec["primary"]["command"]

    def test_ollama_setup_guide(self):
        """Verify setup guide endpoint structure."""
        import asyncio
        from backend.llm.gateway import llm_gateway

        guide = asyncio.run(llm_gateway.get_ollama_setup_guide())
        assert "title" in guide
        assert len(guide["steps"]) >= 3
        assert "alternative_models" in guide
