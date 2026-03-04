"""Tests for the agentic swarm: orchestrator, commit agent, swarm runner."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from digital_brain.brain import DigitalBrain
from digital_brain.thread import DigitalThread
from middleware.wave_runtime import WaveformRuntime
from physics_search.engine import PhysicsSearchEngine
from schemas import CommitPlan, SwarmState
from swarm.commit_agent import CommitAgent
from swarm.orchestrator import SwarmOrchestrator
from swarm.swarm_runner import SwarmRunner


def _make_components():
    brain = DigitalBrain()
    thread = DigitalThread()
    runtime = WaveformRuntime()
    search = PhysicsSearchEngine()

    # Seed some knowledge
    repo = brain.create_repo("test-repo", "testing", "Test knowledge")
    entry = brain.file_knowledge(repo.repo_id, "Test entry content for retrieval")
    search.index_entry(entry)

    return brain, thread, runtime, search


# =====================================================================
# SwarmOrchestrator tests
# =====================================================================

class TestSwarmOrchestrator:
    def test_process_prompt(self):
        brain, thread, runtime, search = _make_components()
        orch = SwarmOrchestrator(brain, thread, runtime, search)
        result = orch.process_prompt("search for test data")
        assert "state_id" in result
        assert "results" in result
        assert "observable" in result

    def test_generate_plan(self):
        brain, thread, runtime, search = _make_components()
        orch = SwarmOrchestrator(brain, thread, runtime, search)
        plan = orch.generate_plan("create new feature")
        assert isinstance(plan, CommitPlan)
        assert len(plan.message) > 0
        assert orch.plan_count == 1

    def test_dispatch_agents(self):
        brain, thread, runtime, search = _make_components()
        orch = SwarmOrchestrator(brain, thread, runtime, search)
        plan = orch.generate_plan("add tests")
        tasks = orch.dispatch_agents(plan)
        assert len(tasks) > 0
        assert all(t.state == SwarmState.PLANNING for t in tasks)


# =====================================================================
# CommitAgent tests
# =====================================================================

class TestCommitAgent:
    def test_create_commit(self):
        agent = CommitAgent()
        plan = CommitPlan(message="test commit", files_changed=["a.py"])
        commit = agent.create_commit(plan)
        assert "commit_id" in commit
        assert commit["status"] == "created"
        assert agent.commit_count == 1

    def test_stage_and_merge(self):
        agent = CommitAgent()
        p1 = CommitPlan(message="first", files_changed=["a.py"])
        p2 = CommitPlan(message="second", files_changed=["b.py"])

        agent.stage_changes(p1)
        agent.stage_changes(p2)
        assert agent.staged_count == 2

        merge = agent.prepare_merge()
        assert merge["status"] == "ready"
        assert merge["total_commits"] == 2
        assert agent.staged_count == 0  # cleared after merge

    def test_prepare_merge_empty(self):
        agent = CommitAgent()
        merge = agent.prepare_merge()
        assert merge["status"] == "nothing_to_merge"


# =====================================================================
# SwarmRunner tests
# =====================================================================

class TestSwarmRunner:
    def test_initial_state_is_idle(self):
        runner = SwarmRunner()
        assert runner.state == SwarmState.IDLE

    def test_step_idle_needs_prompt(self):
        runner = SwarmRunner()
        result = runner.step()
        assert result["status"] == "idle"

    def test_step_through_pipeline(self):
        brain, thread, runtime, search = _make_components()
        runner = SwarmRunner(brain, thread, runtime, search)

        r1 = runner.step("build feature X")
        assert r1["status"] == "planning"
        assert runner.state == SwarmState.PLANNING

        r2 = runner.step()
        assert r2["status"] == "executing"
        assert runner.state == SwarmState.EXECUTING

        r3 = runner.step()
        assert r3["status"] == "committing"
        assert runner.state == SwarmState.COMMITTING

        r4 = runner.step()
        assert r4["status"] == "merged"
        assert runner.state == SwarmState.MERGED

    def test_full_run(self):
        brain, thread, runtime, search = _make_components()
        runner = SwarmRunner(brain, thread, runtime, search)

        result = runner.run("implement search feature")
        assert "pipeline" in result
        assert result["final_state"] in ("merged", "idle")
        assert result["total_commits"] >= 1

    def test_invalid_transition_raises(self):
        runner = SwarmRunner()
        try:
            runner._transition(SwarmState.COMMITTING)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_get_state(self):
        runner = SwarmRunner()
        state = runner.get_state()
        assert state["state"] == "idle"
        assert "history" in state
