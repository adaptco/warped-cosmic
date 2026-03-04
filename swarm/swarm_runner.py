"""Swarm Runner — FSM-driven agentic swarm pipeline.

Runs the full swarm lifecycle:
IDLE → PLANNING → EXECUTING → COMMITTING → MERGED (or FAILED).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from digital_brain.brain import DigitalBrain
from digital_brain.thread import DigitalThread
from middleware.wave_runtime import WaveformRuntime
from physics_search.engine import PhysicsSearchEngine
from schemas import CommitPlan, SwarmState, SwarmTask
from swarm.commit_agent import CommitAgent
from swarm.orchestrator import SwarmOrchestrator


# Valid FSM transitions
_TRANSITIONS: Dict[SwarmState, List[SwarmState]] = {
    SwarmState.IDLE: [SwarmState.PLANNING],
    SwarmState.PLANNING: [SwarmState.EXECUTING, SwarmState.FAILED],
    SwarmState.EXECUTING: [SwarmState.COMMITTING, SwarmState.FAILED],
    SwarmState.COMMITTING: [SwarmState.MERGED, SwarmState.FAILED],
    SwarmState.MERGED: [SwarmState.IDLE],
    SwarmState.FAILED: [SwarmState.IDLE],
}


class SwarmRunner:
    """Runs the agentic swarm as a coordinated FSM pipeline.

    Integrates the ``SwarmOrchestrator`` (prompt → plan) and
    ``CommitAgent`` (plan → commit → merge) through a state machine.
    """

    def __init__(
        self,
        brain: Optional[DigitalBrain] = None,
        thread: Optional[DigitalThread] = None,
        runtime: Optional[WaveformRuntime] = None,
        search_engine: Optional[PhysicsSearchEngine] = None,
    ) -> None:
        self._brain = brain or DigitalBrain()
        self._thread = thread or DigitalThread()
        self._runtime = runtime or WaveformRuntime()
        self._search = search_engine or PhysicsSearchEngine()

        self._orchestrator = SwarmOrchestrator(
            self._brain, self._thread, self._runtime, self._search
        )
        self._commit_agent = CommitAgent()

        self._state = SwarmState.IDLE
        self._history: List[Dict[str, Any]] = []
        self._current_plan: Optional[CommitPlan] = None
        self._current_tasks: List[SwarmTask] = []

    # ------------------------------------------------------------------
    # FSM
    # ------------------------------------------------------------------

    @property
    def state(self) -> SwarmState:
        return self._state

    def _transition(self, target: SwarmState) -> None:
        allowed = _TRANSITIONS.get(self._state, [])
        if target not in allowed:
            raise ValueError(
                f"Invalid transition: {self._state.value} → {target.value}"
            )
        self._history.append(
            {"from": self._state.value, "to": target.value}
        )
        self._state = target

    def get_state(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "plan": self._current_plan.model_dump() if self._current_plan else None,
            "tasks": len(self._current_tasks),
            "commits": self._commit_agent.commit_count,
            "history": self._history[-10:],
        }

    # ------------------------------------------------------------------
    # Step engine
    # ------------------------------------------------------------------

    def step(self, prompt: str = "") -> Dict[str, Any]:
        """Advance the swarm by one FSM step.

        - IDLE + prompt → PLANNING (process prompt, generate plan)
        - PLANNING → EXECUTING (dispatch tasks)
        - EXECUTING → COMMITTING (create commits)
        - COMMITTING → MERGED (prepare merge)
        """
        if self._state == SwarmState.IDLE:
            if not prompt:
                return {"status": "idle", "message": "Provide a prompt to start"}
            self._transition(SwarmState.PLANNING)
            ctx = self._orchestrator.process_prompt(prompt)
            self._current_plan = self._orchestrator.generate_plan(prompt, ctx)
            return {
                "status": "planning",
                "plan_id": self._current_plan.plan_id,
                "context": ctx,
            }

        if self._state == SwarmState.PLANNING:
            if self._current_plan is None:
                self._transition(SwarmState.FAILED)
                return {"status": "failed", "error": "No plan generated"}
            self._transition(SwarmState.EXECUTING)
            self._current_tasks = self._orchestrator.dispatch_agents(
                self._current_plan
            )
            for task in self._current_tasks:
                task.state = SwarmState.EXECUTING
                task.result = f"Executed: {task.title}"
            return {
                "status": "executing",
                "tasks": [t.model_dump() for t in self._current_tasks],
            }

        if self._state == SwarmState.EXECUTING:
            if not self._current_plan:
                self._transition(SwarmState.FAILED)
                return {"status": "failed", "error": "No plan to commit"}
            self._transition(SwarmState.COMMITTING)
            commit = self._commit_agent.create_commit(
                self._current_plan, self._current_tasks
            )
            self._commit_agent.stage_changes(self._current_plan)
            return {"status": "committing", "commit": commit}

        if self._state == SwarmState.COMMITTING:
            self._transition(SwarmState.MERGED)
            merge = self._commit_agent.prepare_merge()
            # Reset for next run
            self._current_plan = None
            self._current_tasks = []
            return {"status": "merged", "merge": merge}

        if self._state in (SwarmState.MERGED, SwarmState.FAILED):
            self._transition(SwarmState.IDLE)
            return {"status": "reset_to_idle"}

        return {"status": "unknown_state", "state": self._state.value}

    # ------------------------------------------------------------------
    # Full run
    # ------------------------------------------------------------------

    def run(self, prompt: str) -> Dict[str, Any]:
        """Run the full pipeline from prompt to merge in one call."""
        results: List[Dict[str, Any]] = []

        # Reset if needed
        if self._state not in (SwarmState.IDLE,):
            try:
                self._transition(SwarmState.IDLE)
            except ValueError:
                self._state = SwarmState.IDLE

        # Step through all phases
        r1 = self.step(prompt)
        results.append(r1)

        for _ in range(4):
            r = self.step()
            results.append(r)
            if r.get("status") in ("merged", "failed", "reset_to_idle"):
                break

        return {
            "pipeline": results,
            "final_state": self._state.value,
            "total_commits": self._commit_agent.commit_count,
        }

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def brain(self) -> DigitalBrain:
        return self._brain

    @property
    def thread(self) -> DigitalThread:
        return self._thread

    @property
    def orchestrator(self) -> SwarmOrchestrator:
        return self._orchestrator

    @property
    def commit_agent(self) -> CommitAgent:
        return self._commit_agent
