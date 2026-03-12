"""Tests for the MCP server tools and agent protocol."""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas import AgentCapability, AgentMessage
from server.agent_protocol import AgentProtocol


# =====================================================================
# AgentProtocol tests
# =====================================================================

class TestAgentProtocol:
    def test_register_agent(self):
        proto = AgentProtocol()
        hs = proto.handshake(
            "test-agent",
            capabilities=[AgentCapability(name="code_gen", description="Generate code")],
        )
        assert proto.agent_count == 1
        agents = proto.list_agents()
        assert len(agents) == 1
        assert agents[0]["agent_name"] == "test-agent"

    def test_handshake_returns_valid(self):
        proto = AgentProtocol()
        hs = proto.handshake("agent-a")
        assert hs.agent_name == "agent-a"
        assert hs.version == "1.0.0"

    def test_route_message_delivered(self):
        proto = AgentProtocol()
        hs = proto.handshake("receiver-agent")
        result = proto.send(
            sender="sender-agent",
            receiver=hs.agent_id,
            action="execute",
            payload={"code": "print('hello')"},
        )
        assert result["status"] == "delivered"
        assert proto.message_count == 1

    def test_route_message_undeliverable(self):
        proto = AgentProtocol()
        result = proto.send(
            sender="a", receiver="nonexistent", action="test"
        )
        assert result["status"] == "undeliverable"

    def test_get_inbox(self):
        proto = AgentProtocol()
        hs = proto.handshake("inbox-agent")
        proto.send("sender", hs.agent_id, "msg1")
        proto.send("sender", hs.agent_id, "msg2")

        inbox = proto.get_inbox(hs.agent_id)
        assert len(inbox) == 2

    def test_find_agent_by_capability(self):
        proto = AgentProtocol()
        proto.handshake(
            "coding-agent",
            capabilities=[
                AgentCapability(name="code_gen"),
                AgentCapability(name="refactor"),
            ],
        )
        proto.handshake(
            "test-agent",
            capabilities=[AgentCapability(name="test_gen")],
        )

        coders = proto.find_agent_by_capability("code_gen")
        assert len(coders) == 1

        testers = proto.find_agent_by_capability("test_gen")
        assert len(testers) == 1

        nones = proto.find_agent_by_capability("nonexistent")
        assert len(nones) == 0

    def test_get_capabilities(self):
        proto = AgentProtocol()
        hs = proto.handshake(
            "cap-agent",
            capabilities=[AgentCapability(name="cap_a"), AgentCapability(name="cap_b")],
        )
        caps = proto.get_capabilities(hs.agent_id)
        assert len(caps) == 2
        assert caps[0].name == "cap_a"

    def test_sync_from_documents_registers_document_agents(self, tmp_path: Path):
        registry = tmp_path / "AGENTS.md"
        registry.write_text(
            """### CLAUDE_BROWSER
**Role:** Browser Automation & Rework Triage Agent · Capsule: `Forge.Trace`

#### Skill.md

```yaml
skill: browser-automation-rework-triage
version: "1.0.0"
capsule: Forge.Trace

capabilities:
  - Playwright browser task execution from natural-language specifications
  - Telemetry-backed rework hotspot summarization and merge conflict triage
```

#### Tools.md

```yaml
tools:
  - name: browser_agent
    script: agent-forge/agent-forge/agents/browser/agent.py
```
""",
            encoding="utf-8",
        )

        proto = AgentProtocol()
        proto.sync_from_documents([registry])

        agents = proto.list_agents()
        browser = next(agent for agent in agents if agent["agent_name"] == "CLAUDE_BROWSER")
        assert browser["kind"] == "document"
        assert browser["role"] == "Browser Automation & Rework Triage Agent"
        assert any(source.endswith("AGENTS.md") for source in browser["sources"])

        matches = proto.find_agent_by_capability(
            "Telemetry-backed rework hotspot summarization and merge conflict triage"
        )
        assert browser["agent_id"] in matches


# =====================================================================
# MCP Server tool integration (without starting server)
# =====================================================================

class TestMCPServerTools:
    """Test the MCP server tool functions directly (not via network)."""

    def test_brain_file_and_search(self):
        """Test brain_file and brain_search tool functions."""
        import json
        # Import the server module to access the global instances
        from server import mcp_server
        from digital_brain.brain import DigitalBrain

        # Use the server's global brain instance
        brain = mcp_server.brain
        search = mcp_server.search_engine

        # Test via the brain directly (tools are FastMCP-wrapped)
        repo = brain.create_repo("test-mcp", "testing", "MCP test repo")
        entry = brain.file_knowledge(
            repo.repo_id, "MCP protocol data for testing"
        )
        search.index_entry(entry)

        results = brain.retrieve("MCP protocol")
        assert len(results) > 0

    def test_swarm_runner_accessible(self):
        """Verify the swarm runner is accessible from the server module."""
        from server import mcp_server

        runner = mcp_server.swarm_runner
        state = runner.get_state()
        assert state["state"] == "idle"

    def test_protocol_has_builtin_agents(self):
        """Verify built-in agents are pre-registered."""
        from server import mcp_server

        agents = mcp_server.protocol.list_agents()
        names = [a["agent_name"] for a in agents]
        assert "digital_brain" in names
        assert "swarm_orchestrator" in names
        assert "commit_agent" in names
        digital_brain = next(a for a in agents if a["agent_name"] == "digital_brain")
        assert digital_brain["runtime_binding"]["boo_binding"] == "ECHO"
