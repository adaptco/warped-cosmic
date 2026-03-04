"""Firestore persistence layer for the Digital Brain.

Syncs in-memory knowledge repos, entries, threads, agents, and swarm
state to Cloud Firestore in the moe-router-98693480 project.

Requires: pip install firebase-admin
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    _FIREBASE_AVAILABLE = True
except ModuleNotFoundError:
    _FIREBASE_AVAILABLE = False


class FirestoreSync:
    """Persistence adapter: Digital Brain ⇄ Firestore.

    Falls back to no-op mode when firebase-admin is not installed,
    allowing the system to run locally without Firebase.
    """

    def __init__(
        self,
        project_id: str = "moe-router-98693480",
        credential_path: Optional[str] = None,
    ) -> None:
        self._project_id = project_id
        self._db = None
        self._enabled = False

        if not _FIREBASE_AVAILABLE:
            print("[FirestoreSync] firebase-admin not installed — running in memory-only mode")
            return

        try:
            # Use Application Default Credentials or explicit key
            if credential_path and os.path.exists(credential_path):
                cred = credentials.Certificate(credential_path)
            else:
                cred = credentials.ApplicationDefault()

            # Initialize only once
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(cred, {"projectId": project_id})

            self._db = firestore.client()
            self._enabled = True
            print(f"[FirestoreSync] Connected to project: {project_id}")
        except Exception as e:
            print(f"[FirestoreSync] Init failed ({e}) — running in memory-only mode")

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    # Repos
    # ------------------------------------------------------------------

    def save_repo(self, repo_data: Dict[str, Any]) -> None:
        """Persist a knowledge repository to Firestore."""
        if not self._enabled:
            return
        repo_id = repo_data.get("repo_id", "")
        doc = _serialize(repo_data)
        self._db.collection("repos").document(repo_id).set(doc)

    def load_repos(self) -> List[Dict[str, Any]]:
        """Load all repositories from Firestore."""
        if not self._enabled:
            return []
        docs = self._db.collection("repos").stream()
        return [_deserialize(d.to_dict()) for d in docs]

    # ------------------------------------------------------------------
    # Entries
    # ------------------------------------------------------------------

    def save_entry(self, repo_id: str, entry_data: Dict[str, Any]) -> None:
        """Persist a knowledge entry under its repo."""
        if not self._enabled:
            return
        entry_id = entry_data.get("entry_id", "")
        doc = _serialize(entry_data)
        self._db.collection("repos").document(repo_id).collection("entries").document(entry_id).set(doc)

    def load_entries(self, repo_id: str) -> List[Dict[str, Any]]:
        """Load all entries for a repo."""
        if not self._enabled:
            return []
        docs = self._db.collection("repos").document(repo_id).collection("entries").stream()
        return [_deserialize(d.to_dict()) for d in docs]

    # ------------------------------------------------------------------
    # Threads
    # ------------------------------------------------------------------

    def save_thread(self, thread_data: Dict[str, Any]) -> None:
        """Persist a digital thread node."""
        if not self._enabled:
            return
        node_id = thread_data.get("node_id", "")
        doc = _serialize(thread_data)
        self._db.collection("threads").document(node_id).set(doc)

    def load_threads(self) -> List[Dict[str, Any]]:
        """Load all thread nodes."""
        if not self._enabled:
            return []
        docs = self._db.collection("threads").stream()
        return [_deserialize(d.to_dict()) for d in docs]

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    def save_agent(self, agent_data: Dict[str, Any]) -> None:
        """Persist an agent registration."""
        if not self._enabled:
            return
        agent_id = agent_data.get("agent_id", "")
        doc = _serialize(agent_data)
        self._db.collection("agents").document(agent_id).set(doc)

    def load_agents(self) -> List[Dict[str, Any]]:
        """Load all registered agents."""
        if not self._enabled:
            return []
        docs = self._db.collection("agents").stream()
        return [_deserialize(d.to_dict()) for d in docs]

    # ------------------------------------------------------------------
    # Swarm state
    # ------------------------------------------------------------------

    def save_swarm_state(self, state_data: Dict[str, Any]) -> None:
        """Persist the current swarm pipeline state."""
        if not self._enabled:
            return
        doc = _serialize(state_data)
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._db.collection("swarm").document("current_state").set(doc)

    def load_swarm_state(self) -> Optional[Dict[str, Any]]:
        """Load the last persisted swarm state."""
        if not self._enabled:
            return None
        doc = self._db.collection("swarm").document("current_state").get()
        if doc.exists:
            return _deserialize(doc.to_dict())
        return None

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def save_message(self, message_data: Dict[str, Any]) -> None:
        """Persist an agent message."""
        if not self._enabled:
            return
        msg_id = message_data.get("message_id", "")
        doc = _serialize(message_data)
        self._db.collection("messages").document(msg_id).set(doc)

    def load_messages(self, agent_id: str) -> List[Dict[str, Any]]:
        """Load messages for an agent (receiver inbox)."""
        if not self._enabled:
            return []
        docs = (
            self._db.collection("messages")
            .where("receiver", "==", agent_id)
            .stream()
        )
        return [_deserialize(d.to_dict()) for d in docs]

    # ------------------------------------------------------------------
    # Bulk sync
    # ------------------------------------------------------------------

    def sync_brain_to_firestore(self, brain) -> Dict[str, int]:
        """Sync the entire in-memory brain to Firestore."""
        if not self._enabled:
            return {"status": "disabled"}

        counts = {"repos": 0, "entries": 0}
        for repo in brain.list_repos():
            self.save_repo(repo.model_dump())
            counts["repos"] += 1

            for entry in brain._entries.get(repo.repo_id, []):
                self.save_entry(repo.repo_id, entry.model_dump())
                counts["entries"] += 1

        return counts


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Python objects to Firestore-safe types."""
    result = {}
    for k, v in data.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, list) and v and isinstance(v[0], float):
            # Store float vectors as JSON string (Firestore array limit)
            result[k] = json.dumps(v)
        elif isinstance(v, dict):
            result[k] = _serialize(v)
        else:
            result[k] = v
    return result


def _deserialize(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Firestore doc back to Python types."""
    result = {}
    for k, v in data.items():
        if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    result[k] = parsed
                    continue
            except (json.JSONDecodeError, ValueError):
                pass
        if isinstance(v, dict):
            result[k] = _deserialize(v)
        else:
            result[k] = v
    return result
