"""FastAPI server that wraps MCP tools as HTTP REST endpoints.

This is the production API layer — every MCP tool is exposed as a
standard HTTP endpoint for VM deployment and CI/CD health checks.
"""

from __future__ import annotations

import json
import sys
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import MCP_PORT, MCP_SERVER_NAME
from digital_brain.brain import DigitalBrain
from digital_brain.thread import DigitalThread
from middleware.wave_runtime import WaveformRuntime
from physics_search.engine import PhysicsSearchEngine
from schemas import AgentCapability, CommitPlan
from server.agent_protocol import AgentProtocol, default_agent_document_paths
from server.firestore_sync import FirestoreSync
from swarm.swarm_runner import SwarmRunner


# ---------------------------------------------------------------------------
# Global instances (initialised in lifespan)
# ---------------------------------------------------------------------------
brain: DigitalBrain
thread: DigitalThread
runtime: WaveformRuntime
search_engine: PhysicsSearchEngine
swarm_runner: SwarmRunner
protocol: AgentProtocol
fs_sync: FirestoreSync


def _seed(b: DigitalBrain, s: PhysicsSearchEngine) -> None:
    repos = [
        ("orchestration", "systems", "Multi-agent pipeline orchestration patterns"),
        ("physics", "science", "Physics-informed neural networks and wave models"),
        ("git-ops", "devops", "Git merge workflows and commit automation"),
        ("vector-search", "ml", "Vector embeddings and semantic search"),
        ("mcp-protocol", "protocol", "Model Context Protocol for agent-to-agent comms"),
    ]
    for name, domain, desc in repos:
        repo = b.create_repo(name, domain, desc)
        entry = b.file_knowledge(repo.repo_id, desc, source="seed", tags=[domain])
        s.index_entry(entry)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global brain, thread, runtime, search_engine, swarm_runner, protocol, fs_sync

    brain = DigitalBrain()
    thread = DigitalThread()
    runtime = WaveformRuntime()
    search_engine = PhysicsSearchEngine()
    _seed(brain, search_engine)

    swarm_runner = SwarmRunner(brain, thread, runtime, search_engine)

    # Firestore persistence (graceful fallback if not configured)
    fs_sync = FirestoreSync(project_id="moe-router-98693480")

    protocol = AgentProtocol()
    protocol.sync_from_documents(default_agent_document_paths())
    protocol.handshake(
        "digital_brain",
        capabilities=[
            AgentCapability(name="brain_search", description="Search the knowledge base"),
            AgentCapability(name="brain_file", description="File knowledge into repos"),
        ],
    )
    protocol.handshake(
        "swarm_orchestrator",
        capabilities=[
            AgentCapability(name="swarm_dispatch", description="Dispatch agentic swarm tasks"),
            AgentCapability(name="swarm_status", description="Get swarm pipeline status"),
        ],
    )
    protocol.handshake(
        "commit_agent",
        capabilities=[
            AgentCapability(name="commit_create", description="Create git commits"),
            AgentCapability(name="thread_stitch", description="Stitch digital threads"),
        ],
    )

    yield  # app is running


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title=f"{MCP_SERVER_NAME} API",
    description="Production REST API for the Digital Brain agent system — MCP tools exposed as HTTP endpoints.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class BrainSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class BrainFileRequest(BaseModel):
    repo_name: str
    domain: str
    content: str


class ThreadStitchRequest(BaseModel):
    source_repo: str
    target_repo: str
    summary: str = ""


class SwarmDispatchRequest(BaseModel):
    prompt: str


class CommitCreateRequest(BaseModel):
    message: str
    files: str = ""


class AgentSendRequest(BaseModel):
    sender: str
    receiver: str
    action: str
    payload: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check for Docker / load balancer probes."""
    return {
        "status": "ok",
        "service": MCP_SERVER_NAME,
        "brain_repos": brain.repo_count,
        "brain_entries": brain.entry_count,
        "search_index": search_engine.index_size,
        "swarm_state": swarm_runner.state.value,
        "firestore": "connected" if fs_sync.enabled else "memory-only",
        "firebase_project": "moe-router-98693480",
    }


@app.post("/brain/search")
async def brain_search(req: BrainSearchRequest):
    """Search the Digital Brain for relevant knowledge entries."""
    results = brain.retrieve(req.query, top_k=req.top_k)
    return {"results": [r.model_dump() for r in results]}


@app.post("/brain/file")
async def brain_file(req: BrainFileRequest):
    """File knowledge into a Digital Brain repository."""
    repo = None
    for r in brain.list_repos():
        if r.name == req.repo_name:
            repo = r
            break
    if repo is None:
        repo = brain.create_repo(req.repo_name, req.domain)

    entry = brain.file_knowledge(repo.repo_id, req.content, source="api")
    search_engine.index_entry(entry)

    # Persist to Firestore
    fs_sync.save_repo(repo.model_dump())
    fs_sync.save_entry(repo.repo_id, entry.model_dump())

    return {"repo_id": repo.repo_id, "entry_id": entry.entry_id}


@app.post("/thread/stitch")
async def thread_stitch(req: ThreadStitchRequest):
    """Stitch a digital thread between two knowledge repos."""
    node = thread.stitch(req.source_repo, req.target_repo, content_summary=req.summary)
    return {"node_id": node.node_id, "coherence": node.coherence}


@app.post("/swarm/dispatch")
async def swarm_dispatch(req: SwarmDispatchRequest):
    """Dispatch the agentic swarm to process a prompt through the full pipeline."""
    result = swarm_runner.run(req.prompt)
    return result


@app.get("/swarm/status")
async def swarm_status():
    """Get the current status of the agentic swarm pipeline."""
    return swarm_runner.get_state()


@app.post("/commit/create")
async def commit_create(req: CommitCreateRequest):
    """Create a git commit with the given message and file list."""
    file_list = [f.strip() for f in req.files.split(",") if f.strip()] or [
        "generated/default.py"
    ]
    plan = CommitPlan(message=req.message, files_changed=file_list)
    commit = swarm_runner.commit_agent.create_commit(plan)
    return commit


@app.get("/agents")
async def agent_list():
    """List all registered agents in the MCP network."""
    return {"agents": protocol.list_agents()}


@app.post("/agents/send")
async def agent_send(req: AgentSendRequest):
    """Send a message between two agents in the MCP network."""
    result = protocol.send(req.sender, req.receiver, req.action, req.payload)
    return result


@app.post("/firestore/sync")
async def firestore_sync():
    """Sync the entire in-memory brain to Firestore."""
    counts = fs_sync.sync_brain_to_firestore(brain)
    return {"status": "synced", "counts": counts, "firestore_enabled": fs_sync.enabled}


@app.get("/firestore/status")
async def firestore_status():
    """Check Firestore connection status."""
    return {
        "enabled": fs_sync.enabled,
        "project": "moe-router-98693480",
        "brain_repos": brain.repo_count,
        "brain_entries": brain.entry_count,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT)
