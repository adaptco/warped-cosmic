"""Digital Brain MCP Server — exposes the full system as MCP tools.

Tools: brain_search, brain_file, thread_stitch, swarm_dispatch,
swarm_status, commit_create.

Serves as the network backbone for Agent-to-Agent interactions via
the Model Context Protocol.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

# FastMCP import — compatible with both standalone and mcp-sdk installs
try:
    from fastmcp import FastMCP
except ModuleNotFoundError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError:
        # Graceful fallback for environments without MCP
        FastMCP = None  # type: ignore[assignment,misc]

from config import MCP_SERVER_NAME
from digital_brain.brain import DigitalBrain
from digital_brain.thread import DigitalThread
from middleware.wave_runtime import WaveformRuntime
from physics_search.engine import PhysicsSearchEngine
from schemas import AgentCapability
from server.agent_protocol import AgentProtocol, default_agent_document_paths
from swarm.commit_agent import CommitAgent
from swarm.orchestrator import SwarmOrchestrator
from swarm.swarm_runner import SwarmRunner


# ---------------------------------------------------------------------------
# Global instances (singleton lifecycle)
# ---------------------------------------------------------------------------
brain = DigitalBrain()
thread = DigitalThread()
runtime = WaveformRuntime()
search_engine = PhysicsSearchEngine()
swarm_runner = SwarmRunner(brain, thread, runtime, search_engine)
orchestrator = swarm_runner.orchestrator
commit_agent = swarm_runner.commit_agent
protocol = AgentProtocol()
protocol.sync_from_documents(default_agent_document_paths())

# Register built-in agents
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

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
if FastMCP is not None:
    mcp = FastMCP(MCP_SERVER_NAME)

    @mcp.tool()
    def brain_search(query: str, top_k: int = 5) -> str:
        """Search the Digital Brain for relevant knowledge entries."""
        results = brain.retrieve(query, top_k=top_k)
        return json.dumps([r.model_dump() for r in results], default=str)

    @mcp.tool()
    def brain_file(repo_name: str, domain: str, content: str) -> str:
        """File knowledge into a Digital Brain repository.

        Creates the repo if it doesn't exist, then files the content.
        """
        # Find or create repo
        repo = None
        for r in brain.list_repos():
            if r.name == repo_name:
                repo = r
                break
        if repo is None:
            repo = brain.create_repo(repo_name, domain)

        entry = brain.file_knowledge(repo.repo_id, content, source="mcp_tool")
        # Index for physics search
        search_engine.index_entry(entry)
        return json.dumps(
            {"repo_id": repo.repo_id, "entry_id": entry.entry_id}, default=str
        )

    @mcp.tool()
    def thread_stitch(source_repo: str, target_repo: str, summary: str = "") -> str:
        """Stitch a digital thread between two knowledge repos."""
        node = thread.stitch(source_repo, target_repo, content_summary=summary)
        return json.dumps(
            {"node_id": node.node_id, "coherence": node.coherence}, default=str
        )

    @mcp.tool()
    def swarm_dispatch(prompt: str) -> str:
        """Dispatch the agentic swarm to process a prompt through the full pipeline."""
        result = swarm_runner.run(prompt)
        return json.dumps(result, default=str)

    @mcp.tool()
    def swarm_status() -> str:
        """Get the current status of the agentic swarm pipeline."""
        return json.dumps(swarm_runner.get_state(), default=str)

    @mcp.tool()
    def commit_create(message: str, files: str = "") -> str:
        """Create a git commit with the given message and file list."""
        from schemas import CommitPlan

        file_list = [f.strip() for f in files.split(",") if f.strip()] or [
            "generated/default.py"
        ]
        plan = CommitPlan(message=message, files_changed=file_list)
        commit = commit_agent.create_commit(plan)
        return json.dumps(commit, default=str)

    @mcp.tool()
    def agent_list() -> str:
        """List all registered agents in the MCP network."""
        return json.dumps(
            {
                "agents": protocol.list_agents(),
                "runtime_product_delivery": protocol.runtime_product_delivery_schema(),
            },
            default=str,
        )

    @mcp.tool()
    def agent_send(sender: str, receiver: str, action: str, payload: str = "{}") -> str:
        """Send a message between two agents in the MCP network."""
        result = protocol.send(sender, receiver, action, json.loads(payload))
        return json.dumps(result, default=str)

else:
    mcp = None  # type: ignore[assignment]


def run_server() -> None:
    """Start the MCP server."""
    if mcp is None:
        print("ERROR: FastMCP not available. Install with: pip install fastmcp")
        sys.exit(1)
    mcp.run()
