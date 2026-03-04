"""Commit Agent — creates git commits from orchestrated work items.

Uses the Digital Thread to maintain commit coherence across merges,
generating structured commit plans with file diffs and messages.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import COMMIT_PREFIX, DEFAULT_BRANCH
from schemas import CommitPlan, SwarmState, SwarmTask


class CommitAgent:
    """Agent that creates git commits from swarm work items.

    Maintains a ledger of prepared commits and can stage changes
    for merge into a target branch.
    """

    def __init__(
        self,
        branch: str = DEFAULT_BRANCH,
        prefix: str = COMMIT_PREFIX,
    ) -> None:
        self._branch = branch
        self._prefix = prefix
        self._commits: List[Dict[str, Any]] = []
        self._staged: List[CommitPlan] = []

    # ------------------------------------------------------------------
    # Commit creation
    # ------------------------------------------------------------------

    def create_commit(
        self,
        plan: CommitPlan,
        task_results: Optional[List[SwarmTask]] = None,
    ) -> Dict[str, Any]:
        """Create a commit record from a plan and optional task results."""
        commit = {
            "commit_id": str(uuid.uuid4()),
            "message": f"{self._prefix} {plan.message}",
            "branch": plan.branch or self._branch,
            "files_changed": list(plan.files_changed),
            "diff_summary": plan.diff_summary,
            "plan_id": plan.plan_id,
            "parent_sha": plan.parent_sha,
            "tasks": [t.task_id for t in (task_results or [])],
            "status": "created",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._commits.append(commit)
        return commit

    # ------------------------------------------------------------------
    # Staging
    # ------------------------------------------------------------------

    def stage_changes(self, plan: CommitPlan) -> Dict[str, Any]:
        """Stage a commit plan for the next merge."""
        self._staged.append(plan)
        return {
            "staged_plan_id": plan.plan_id,
            "staged_count": len(self._staged),
            "branch": self._branch,
        }

    def prepare_merge(self) -> Dict[str, Any]:
        """Prepare all staged changes for merge into the target branch.

        Returns a merge manifest with all staged commit plans.
        """
        if not self._staged:
            return {"status": "nothing_to_merge", "branch": self._branch}

        merge_id = str(uuid.uuid4())
        manifest = {
            "merge_id": merge_id,
            "branch": self._branch,
            "plans": [p.plan_id for p in self._staged],
            "total_files": sum(len(p.files_changed) for p in self._staged),
            "total_commits": len(self._staged),
            "status": "ready",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Clear staging area
        self._staged = []
        return manifest

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def commit_count(self) -> int:
        return len(self._commits)

    @property
    def staged_count(self) -> int:
        return len(self._staged)

    def get_commits(self) -> List[Dict[str, Any]]:
        return list(self._commits)

    def get_latest_commit(self) -> Optional[Dict[str, Any]]:
        return self._commits[-1] if self._commits else None
