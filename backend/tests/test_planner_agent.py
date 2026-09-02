"""Tests for the Implementation Planner Agent and its coordinator integration.

Unit tests only — no network access, no ADK runner.
"""

import pytest

from app.models.schemas import (
    ImplementationPlanResponse,
    ImplementationStep,
)


# ---------- Schema validation ----------


class TestImplementationStep:
    def test_defaults(self):
        step = ImplementationStep(step_number=1, title="Do it", description="Do the thing")
        assert step.files_to_modify == []
        assert step.code_hints == ""

    def test_extra_fields_ignored(self):
        step = ImplementationStep(
            step_number=1,
            title="T",
            description="D",
            unknown_field="x",
        )
        assert not hasattr(step, "unknown_field")

    def test_full_step(self):
        step = ImplementationStep(
            step_number=2,
            title="Write test",
            description="Add a pytest case",
            files_to_modify=["tests/test_foo.py"],
            code_hints="Use pytest.fixture",
        )
        assert step.step_number == 2
        assert step.files_to_modify == ["tests/test_foo.py"]
        assert "pytest" in step.code_hints


class TestImplementationPlanResponse:
    def test_defaults(self):
        plan = ImplementationPlanResponse(title="Plan it")
        assert plan.steps == []
        assert plan.risks == []
        assert plan.edge_cases == []
        assert plan.estimated_complexity == "medium"
        assert plan.files_overview == []

    def test_extra_fields_ignored(self):
        plan = ImplementationPlanResponse(title="Plan", mystery_key="x")
        assert not hasattr(plan, "mystery_key")

    def test_with_steps(self):
        plan = ImplementationPlanResponse(
            title="Fix bug",
            steps=[
                {
                    "step_number": 1,
                    "title": "Find it",
                    "description": "Locate the bug",
                }
            ],
        )
        assert len(plan.steps) == 1
        assert plan.steps[0].title == "Find it"

    def test_complexity_values(self):
        for value in ("low", "medium", "high"):
            plan = ImplementationPlanResponse(title="T", estimated_complexity=value)
            assert plan.estimated_complexity == value

    def test_roundtrip_dict(self):
        plan = ImplementationPlanResponse(
            title="Roundtrip",
            issue_summary="Summary here",
            steps=[
                ImplementationStep(
                    step_number=1,
                    title="Step one",
                    description="Do it",
                    files_to_modify=["src/main.py"],
                    code_hints="Use async",
                )
            ],
            risks=["Risk A"],
            edge_cases=["Edge B"],
            testing_strategy="Run pytest",
            estimated_complexity="low",
            prerequisite_knowledge=["Python"],
            files_overview=["src/main.py", "tests/"],
        )
        dumped = plan.model_dump()
        restored = ImplementationPlanResponse(**dumped)
        assert restored.title == plan.title
        assert len(restored.steps) == 1
        assert restored.steps[0].files_to_modify == ["src/main.py"]


# ---------- build_planner_agent factory ----------


class TestBuildPlannerAgent:
    def test_creates_agent_instance(self):
        from google.adk.agents import Agent
        from app.agents.planner_agent import build_planner_agent

        agent = build_planner_agent("fake-token")
        assert isinstance(agent, Agent)

    def test_agent_name(self):
        from app.agents.planner_agent import build_planner_agent

        agent = build_planner_agent("fake-token")
        assert agent.name == "implementation_planner"

    def test_different_tokens_yield_distinct_agents(self):
        from app.agents.planner_agent import build_planner_agent

        a1 = build_planner_agent("token-alice")
        a2 = build_planner_agent("token-bob")
        assert a1 is not a2


# ---------- _fallback_implementation_plan (no network) ----------


class TestFallbackImplementationPlan:
    """Test the fallback plan builder using mocked GitHub tool responses."""

    @pytest.mark.asyncio
    async def test_returns_valid_plan(self, monkeypatch):
        from app.agents.coordinator import _fallback_implementation_plan

        fake_issue = {
            "title": "Fix the widget",
            "body": "The widget is broken",
            "labels": [{"name": "bug"}, {"name": "good first issue"}],
            "comments": 3,
            "number": 42,
        }
        monkeypatch.setattr(
            "app.agents.coordinator.fetch_issue_details",
            lambda *args, **kwargs: _async_return(fake_issue),
        )
        monkeypatch.setattr(
            "app.agents.coordinator.fetch_repo_readme",
            lambda *args, **kwargs: _async_return("# My Project"),
        )
        monkeypatch.setattr(
            "app.agents.coordinator.fetch_repo_tree",
            lambda *args, **kwargs: _async_return([
                {"path": "README.md", "type": "file"},
                {"path": "tests", "type": "dir"},
                {"path": "CONTRIBUTING.md", "type": "file"},
                {"path": "src", "type": "dir"},
            ]),
        )

        plan = await _fallback_implementation_plan("owner", "repo", 42, "token")

        assert isinstance(plan, ImplementationPlanResponse)
        assert "Fix the widget" in plan.title
        assert len(plan.steps) >= 3
        assert plan.estimated_complexity == "medium"
        # Labels become prerequisite knowledge
        assert any("bug" in k.lower() or "good first issue" in k.lower() for k in plan.prerequisite_knowledge)

    @pytest.mark.asyncio
    async def test_raises_on_github_error(self, monkeypatch):
        from app.agents.coordinator import _fallback_implementation_plan

        monkeypatch.setattr(
            "app.agents.coordinator.fetch_issue_details",
            lambda *args, **kwargs: _async_return({"error": "Not found"}),
        )

        with pytest.raises(RuntimeError, match="Not found"):
            await _fallback_implementation_plan("owner", "repo", 1, "token")

    @pytest.mark.asyncio
    async def test_testing_strategy_mentions_tests_when_test_dir_present(self, monkeypatch):
        from app.agents.coordinator import _fallback_implementation_plan

        monkeypatch.setattr(
            "app.agents.coordinator.fetch_issue_details",
            lambda *args, **kwargs: _async_return({
                "title": "Add feature", "body": "", "labels": [], "comments": 0,
            }),
        )
        monkeypatch.setattr(
            "app.agents.coordinator.fetch_repo_readme",
            lambda *args, **kwargs: _async_return(""),
        )
        monkeypatch.setattr(
            "app.agents.coordinator.fetch_repo_tree",
            lambda *args, **kwargs: _async_return([
                {"path": "tests/", "type": "dir"},
            ]),
        )

        plan = await _fallback_implementation_plan("o", "r", 1, "t")
        assert "test" in plan.testing_strategy.lower()

    @pytest.mark.asyncio
    async def test_no_test_dir_no_test_suite_mention(self, monkeypatch):
        from app.agents.coordinator import _fallback_implementation_plan

        monkeypatch.setattr(
            "app.agents.coordinator.fetch_issue_details",
            lambda *args, **kwargs: _async_return({
                "title": "Docs fix", "body": "", "labels": [], "comments": 0,
            }),
        )
        monkeypatch.setattr(
            "app.agents.coordinator.fetch_repo_readme",
            lambda *args, **kwargs: _async_return(""),
        )
        monkeypatch.setattr(
            "app.agents.coordinator.fetch_repo_tree",
            lambda *args, **kwargs: _async_return([
                {"path": "docs/", "type": "dir"},
            ]),
        )

        plan = await _fallback_implementation_plan("o", "r", 1, "t")
        # Should warn that there's no automated test suite
        assert "not appear" in plan.testing_strategy.lower() or "manually" in plan.testing_strategy.lower()


# ---------- Helpers ----------


async def _async_return(value):
    return value
