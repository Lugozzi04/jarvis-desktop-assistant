"""Tests for the Workflow schemas and skills."""

import pytest
from backend.core.schemas import WorkflowAction, WorkflowStep


class TestWorkflowSchemas:
    def test_workflow_action(self):
        steps = [
            WorkflowStep(order=0, skill="apps", action="open",
                        parameters={"app_name": "OBS"}, description="Open OBS"),
            WorkflowStep(order=1, skill="browser", action="open_url",
                        parameters={"url": "https://twitch.tv"}, description="Open Twitch"),
        ]
        wf = WorkflowAction(name="streaming_mode", mode="streaming", steps=steps)
        assert len(wf.steps) == 2
        assert wf.steps[0].skill == "apps"
        assert wf.steps[1].skill == "browser"
