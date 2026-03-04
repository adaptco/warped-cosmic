"""Swarm Orchestrator — coding agent that processes state as a prompt.

Uses the Digital Brain and Physics Search Engine to ground each prompt,
then generates structured work plans that map to git commits.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from digital_brain.brain import DigitalBrain
from digital_brain.thread import DigitalThread
from middleware.wave_runtime import WaveformRuntime
from physics_search.engine import PhysicsSearchEngine
from schemas import CommitPlan, SearchResult, SwarmState, SwarmTask


class SwarmOrchestrator:
    """Coding agent that processes prompts through the full pipeline:

    prompt → wave_state → brain_search → thread_stitch → work_plan → commits.
    """

    def __init__(
        self,
        brain: DigitalBrain,
        thread: DigitalThread,
        runtime: WaveformRuntime,
        search_engine: PhysicsSearchEngine,
    ) -> None:
        self._brain = brain
        self._thread = thread
        self._runtime = runtime
        self._search = search_engine
        self._tasks: Dict[str, SwarmTask] = {}
        self._plans: Dict[str, CommitPlan] = {}

    # ------------------------------------------------------------------
    # Prompt processing
    # ------------------------------------------------------------------

    def process_prompt(self, prompt: str) -> Dict[str, Any]:
        """Process a prompt through the full Digital Brain pipeline.

        1. Encode prompt as a wave state in the middleware runtime
        2. Search the Digital Brain for relevant knowledge
        3. Stitch a digital thread across discovered domains
        4. Return grounded context for downstream code generation
        """
        # 1) Wave state
        state = self._runtime.process_state(prompt)

        # 2) Search
        results = self._search.search([prompt], top_k=5)

        # If brain has entries, also do a direct brain retrieval
        brain_results = self._brain.retrieve(prompt, top_k=3)
        all_results = results + [
            r for r in brain_results if r.entry_id not in {x.entry_id for x in results}
        ]

        # 3) Thread stitching — connect discovered repos
        seen_repos = set()
        for r in all_results:
            if r.repo_id not in seen_repos and len(seen_repos) > 0:
                for prev_repo in list(seen_repos):
                    self._thread.stitch(prev_repo, r.repo_id)
            seen_repos.add(r.repo_id)

        # 4) Observable
        observable = self._runtime.emit_observable(state.state_id)

        return {
            "state_id": state.state_id,
            "prompt": prompt,
            "results": [r.model_dump() for r in all_results],
            "observable": observable,
            "repos_discovered": list(seen_repos),
            "thread_nodes": self._thread.node_count,
        }

    # ------------------------------------------------------------------
    # Plan generation
    # ------------------------------------------------------------------

    def generate_plan(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> CommitPlan:
        """Generate a structured commit plan from a prompt.

        Processes the prompt, retrieves grounded context, and creates
        a ``CommitPlan`` with files-to-change and a commit message.
        """
        ctx = context or self.process_prompt(prompt)
        results = ctx.get("results", [])

        # Derive commit message from prompt + top result
        summary = prompt[:80]
        if results:
            top = results[0]
            content_snip = top.get("content", "")[:60]
            summary = f"{prompt[:50]} — grounded in: {content_snip}"

        plan = CommitPlan(
            message=summary,
            files_changed=[f"generated/{uuid.uuid4().hex[:8]}.py"],
            diff_summary=f"Auto-generated from prompt: {prompt[:100]}",
            tasks=[t.task_id for t in self._tasks.values()],
        )
        self._plans[plan.plan_id] = plan
        return plan

    # ------------------------------------------------------------------
    # Task dispatch
    # ------------------------------------------------------------------

    def dispatch_agents(
        self,
        plan: CommitPlan,
        agent_names: Optional[List[str]] = None,
    ) -> List[SwarmTask]:
        """Create and dispatch SwarmTasks for a commit plan."""
        names = agent_names or ["coder", "tester", "reviewer"]
        tasks: List[SwarmTask] = []

        for i, file in enumerate(plan.files_changed):
            agent = names[i % len(names)]
            task = SwarmTask(
                title=f"Process {file}",
                instruction=f"Generate/validate: {file} per plan {plan.plan_id}",
                state=SwarmState.PLANNING,
                assigned_agent=agent,
            )
            self._tasks[task.task_id] = task
            tasks.append(task)

        return tasks

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    @property
    def plan_count(self) -> int:
        return len(self._plans)

    def get_plan(self, plan_id: str) -> Optional[CommitPlan]:
        return self._plans.get(plan_id)
