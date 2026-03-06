"""Agent Protocol — A2A handshake and routing for the MCP network.

Defines the contract for agent registration, capability advertisement,
and message routing between agents via MCP.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

from schemas import AgentCapability, AgentHandshake, AgentMessage

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT_DOCUMENTS = (
    REPO_ROOT / "docs" / "AGENTS.md",
    REPO_ROOT / "WHAM-Agents-Dashboard" / "AGENTS.md",
)
_SECTION_RE = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|\Z)", re.MULTILINE | re.DOTALL)
_ROLE_RE = re.compile(r"^\*\*Role:\*\*\s*(.+)$", re.MULTILINE)
_YAML_BLOCK_RE = re.compile(
    r"####\s+(?P<label>Skill\.md|Tools\.md)\s+```yaml\s*\n(?P<body>.*?)```",
    re.DOTALL,
)


@dataclass
class AgentDocumentSpec:
    agent_name: str
    role: str = ""
    capsule: str = ""
    version: str = "1.0.0"
    capabilities: List[AgentCapability] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)

    def to_handshake(self) -> AgentHandshake:
        slug = _slugify(self.agent_name)
        return AgentHandshake(
            agent_id=f"doc:{slug}",
            agent_name=self.agent_name,
            capabilities=self.capabilities,
            endpoint=f"registry://{slug}",
            model_id="registry-doc",
            version=self.version,
        )

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "kind": "document",
            "role": self.role,
            "capsule": self.capsule,
            "tools": self.tools,
            "sources": self.sources,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "capsule": self.capsule,
            "version": self.version,
            "capabilities": [cap.model_dump() for cap in self.capabilities],
            "tools": list(self.tools),
            "sources": list(self.sources),
        }


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def default_agent_document_paths(root: Optional[Path] = None) -> List[Path]:
    base = Path(root).resolve() if root else REPO_ROOT
    return [
        base / "docs" / "AGENTS.md",
        base / "WHAM-Agents-Dashboard" / "AGENTS.md",
    ]


def _normalize_agent_name(raw_name: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", raw_name)
    if not tokens:
        return raw_name.strip().upper()
    return "_".join(tokens).upper()


def _extract_yaml_blocks(section_body: str) -> Dict[str, Dict[str, Any]]:
    blocks: Dict[str, Dict[str, Any]] = {}
    for match in _YAML_BLOCK_RE.finditer(section_body):
        label = match.group("label")
        blocks[label] = yaml.safe_load(match.group("body")) or {}
    return blocks


def _parse_role_and_capsule(section_body: str, fallback_capsule: str) -> tuple[str, str]:
    match = _ROLE_RE.search(section_body)
    if not match:
        return "", fallback_capsule

    raw_role = match.group(1).strip()
    if "· Capsule:" not in raw_role:
        return raw_role, fallback_capsule

    role, capsule = raw_role.split("· Capsule:", maxsplit=1)
    return role.strip(), capsule.strip().strip("`")


def _normalize_capabilities(capabilities: Iterable[Any]) -> List[AgentCapability]:
    seen: set[str] = set()
    normalized: List[AgentCapability] = []
    for item in capabilities:
        if not item:
            continue
        text = str(item).strip()
        if not text:
            continue
        name = _slugify(text)
        if name in seen:
            continue
        seen.add(name)
        normalized.append(
            AgentCapability(
                name=name,
                description=text,
                input_schema={"source": "AGENTS.md"},
            )
        )
    return normalized


def _normalize_tools(raw_tools: Iterable[Any]) -> List[str]:
    tools: List[str] = []
    for tool in raw_tools:
        if isinstance(tool, dict):
            label = str(tool.get("name") or "").strip()
            target = str(tool.get("workflow") or tool.get("script") or tool.get("endpoint") or "").strip()
            parts = [part for part in (label, target) if part]
            if parts:
                tools.append(" :: ".join(parts))
        elif tool:
            tools.append(str(tool).strip())
    return tools


def _merge_specs(existing: AgentDocumentSpec, new_spec: AgentDocumentSpec) -> AgentDocumentSpec:
    capability_map = {cap.name: cap for cap in existing.capabilities}
    for cap in new_spec.capabilities:
        capability_map.setdefault(cap.name, cap)
    existing.capabilities = list(capability_map.values())

    tool_names = set(existing.tools)
    for tool in new_spec.tools:
        if tool not in tool_names:
            existing.tools.append(tool)
            tool_names.add(tool)

    source_names = set(existing.sources)
    for source in new_spec.sources:
        if source not in source_names:
            existing.sources.append(source)
            source_names.add(source)

    if not existing.role:
        existing.role = new_spec.role
    if not existing.capsule:
        existing.capsule = new_spec.capsule
    if existing.version == "1.0.0" and new_spec.version != "1.0.0":
        existing.version = new_spec.version

    return existing


def load_agent_document_specs(doc_paths: Optional[Iterable[Path]] = None) -> List[AgentDocumentSpec]:
    paths = [Path(path).resolve() for path in (doc_paths or default_agent_document_paths())]
    merged: Dict[str, AgentDocumentSpec] = {}

    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in _SECTION_RE.finditer(text):
            raw_name = match.group(1)
            section_body = match.group(2)
            blocks = _extract_yaml_blocks(section_body)
            skill = blocks.get("Skill.md", {})
            tools = blocks.get("Tools.md", {})
            capabilities = skill.get("capabilities", [])
            if not capabilities:
                continue

            agent_name = _normalize_agent_name(raw_name)
            role, capsule = _parse_role_and_capsule(section_body, str(skill.get("capsule", "")).strip())
            spec = AgentDocumentSpec(
                agent_name=agent_name,
                role=role,
                capsule=capsule,
                version=str(skill.get("version", "1.0.0")).strip() or "1.0.0",
                capabilities=_normalize_capabilities(capabilities),
                tools=_normalize_tools(tools.get("tools", [])),
                sources=[_display_path(path)],
            )
            merged[agent_name] = _merge_specs(merged[agent_name], spec) if agent_name in merged else spec

    return list(merged.values())


def get_agent_document_spec(
    agent_name: str,
    doc_paths: Optional[Iterable[Path]] = None,
) -> Optional[AgentDocumentSpec]:
    target = _normalize_agent_name(agent_name)
    for spec in load_agent_document_specs(doc_paths):
        if _normalize_agent_name(spec.agent_name) == target:
            return spec
    return None


class AgentProtocol:
    """Manages agent-to-agent interactions in the MCP network.

    Agents register with capabilities; messages are routed based on
    receiver identity and capability matching.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, AgentHandshake] = {}
        self._messages: List[AgentMessage] = []
        self._inbox: Dict[str, List[AgentMessage]] = {}
        self._agent_metadata: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        handshake: AgentHandshake,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register an agent in the network."""
        self._agents[handshake.agent_id] = handshake
        self._inbox.setdefault(handshake.agent_id, [])
        if metadata is not None:
            self._agent_metadata[handshake.agent_id] = metadata
        else:
            self._agent_metadata.setdefault(handshake.agent_id, {})
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
        version: str = "1.0.0",
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentHandshake:
        """Create and register an agent handshake in one call."""
        payload: Dict[str, Any] = {
            "agent_name": agent_name,
            "capabilities": capabilities or [],
            "endpoint": endpoint,
            "model_id": model_id,
            "version": version,
        }
        if agent_id:
            payload["agent_id"] = agent_id
        hs = AgentHandshake(**payload)
        self.register_agent(hs, metadata=metadata)
        return hs

    def sync_from_documents(
        self,
        doc_paths: Optional[Iterable[Path]] = None,
    ) -> List[Dict[str, Any]]:
        """Register agent specifications declared in AGENTS registries."""
        registrations: List[Dict[str, Any]] = []
        for spec in load_agent_document_specs(doc_paths):
            result = self.register_agent(spec.to_handshake(), metadata=spec.to_metadata())
            registrations.append(result)
        return registrations

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

    def get_agent_metadata(self, agent_id: str) -> Dict[str, Any]:
        """Return extra metadata tracked for a registered agent."""
        return dict(self._agent_metadata.get(agent_id, {}))

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their capabilities."""
        records: List[Dict[str, Any]] = []
        for hs in self._agents.values():
            record: Dict[str, Any] = {
                "agent_id": hs.agent_id,
                "agent_name": hs.agent_name,
                "capabilities": [c.name for c in hs.capabilities],
                "model_id": hs.model_id,
                "version": hs.version,
            }
            metadata = self._agent_metadata.get(hs.agent_id, {})
            for key in ("kind", "role", "capsule", "tools", "sources"):
                value = metadata.get(key)
                if value:
                    record[key] = value
            records.append(record)
        return records

    def find_agent_by_capability(self, capability_name: str) -> List[str]:
        """Find agents that advertise a specific capability."""
        matches: List[str] = []
        target = _slugify(capability_name)
        for hs in self._agents.values():
            for cap in hs.capabilities:
                if _slugify(cap.name) == target or _slugify(cap.description) == target:
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
