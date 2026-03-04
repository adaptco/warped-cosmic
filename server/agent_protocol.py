"""Agent Protocol — A2A handshake and routing for the MCP network.

Defines the contract for agent registration, capability advertisement,
and message routing between agents via MCP.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from schemas import AgentCapability, AgentHandshake, AgentMessage


class AgentProtocol:
    """Manages agent-to-agent interactions in the MCP network.

    Agents register with capabilities; messages are routed based on
    receiver identity and capability matching.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, AgentHandshake] = {}
        self._messages: List[AgentMessage] = []
        self._inbox: Dict[str, List[AgentMessage]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent(self, handshake: AgentHandshake) -> Dict[str, Any]:
        """Register an agent in the network."""
        self._agents[handshake.agent_id] = handshake
        self._inbox.setdefault(handshake.agent_id, [])
        return {
            "status": "registered",
            "agent_id": handshake.agent_id,
            "agent_name": handshake.agent_name,
            "capabilities": len(handshake.capabilities),
        }

    def handshake(
        self,
        agent_name: str,
        capabilities: Optional[List[AgentCapability]] = None,
        endpoint: str = "",
        model_id: str = "gpt-4o-mini",
    ) -> AgentHandshake:
        """Create and register an agent handshake in one call."""
        hs = AgentHandshake(
            agent_name=agent_name,
            capabilities=capabilities or [],
            endpoint=endpoint,
            model_id=model_id,
        )
        self.register_agent(hs)
        return hs

    # ------------------------------------------------------------------
    # Message routing
    # ------------------------------------------------------------------

    def route_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Route a message to its target agent's inbox."""
        self._messages.append(message)

        if message.receiver not in self._agents:
            return {
                "status": "undeliverable",
                "reason": f"Agent {message.receiver} not registered",
            }

        self._inbox.setdefault(message.receiver, []).append(message)
        return {
            "status": "delivered",
            "message_id": message.message_id,
            "receiver": message.receiver,
        }

    def send(
        self,
        sender: str,
        receiver: str,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message between two agents (convenience wrapper)."""
        msg = AgentMessage(
            sender=sender,
            receiver=receiver,
            action=action,
            payload=payload or {},
        )
        return self.route_message(msg)

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_inbox(self, agent_id: str) -> List[AgentMessage]:
        """Get all messages in an agent's inbox."""
        return self._inbox.get(agent_id, [])

    def get_capabilities(self, agent_id: str) -> List[AgentCapability]:
        """List capabilities of a registered agent."""
        hs = self._agents.get(agent_id)
        return hs.capabilities if hs else []

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their capabilities."""
        return [
            {
                "agent_id": hs.agent_id,
                "agent_name": hs.agent_name,
                "capabilities": [c.name for c in hs.capabilities],
                "model_id": hs.model_id,
                "version": hs.version,
            }
            for hs in self._agents.values()
        ]

    def find_agent_by_capability(self, capability_name: str) -> List[str]:
        """Find agents that advertise a specific capability."""
        matches: List[str] = []
        for hs in self._agents.values():
            for cap in hs.capabilities:
                if cap.name == capability_name:
                    matches.append(hs.agent_id)
                    break
        return matches

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def message_count(self) -> int:
        return len(self._messages)
