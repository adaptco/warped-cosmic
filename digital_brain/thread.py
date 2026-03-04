"""Digital Thread — stitches knowledge across repos via physics waveforms.

Uses wave interference patterns (superposition, constructive / destructive
interference, phase coherence) to score cross-domain connections and
build a navigable knowledge graph.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from config import WAVE_DECAY, WAVE_FREQUENCY
from schemas import DigitalThreadNode


class DigitalThread:
    """Stitches cross-domain knowledge using wave-based coherence.

    Each connection between two repos is modeled as a wave with amplitude,
    phase and coherence.  ``stitch()``  creates links; ``propagate()``
    updates amplitudes over time; ``collapse_state()`` returns the
    strongest connections for a given origin.
    """

    def __init__(
        self,
        frequency: float = WAVE_FREQUENCY,
        decay: float = WAVE_DECAY,
    ) -> None:
        self._nodes: Dict[str, DigitalThreadNode] = {}
        self._graph: Dict[str, List[str]] = {}  # repo_id -> [node_ids]
        self._frequency = frequency
        self._decay = decay

    # ------------------------------------------------------------------
    # Thread management
    # ------------------------------------------------------------------

    def stitch(
        self,
        source_repo: str,
        target_repo: str,
        amplitude: float = 1.0,
        phase: float = 0.0,
        content_summary: str = "",
    ) -> DigitalThreadNode:
        """Create a threaded connection between two repos."""
        node = DigitalThreadNode(
            source_repo=source_repo,
            target_repo=target_repo,
            amplitude=amplitude,
            phase=phase,
            content_summary=content_summary,
        )
        self._nodes[node.node_id] = node
        self._graph.setdefault(source_repo, []).append(node.node_id)
        self._graph.setdefault(target_repo, []).append(node.node_id)
        return node

    def get_connections(self, repo_id: str) -> List[DigitalThreadNode]:
        """Get all thread nodes connected to a repo."""
        node_ids = self._graph.get(repo_id, [])
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    # ------------------------------------------------------------------
    # Wave propagation
    # ------------------------------------------------------------------

    def propagate(self, time_step: float = 1.0) -> None:
        """Propagate waves through the thread — decay amplitudes over time.

        Applies: A(t+dt) = A(t) * decay * cos(freq * dt + phase)
        Nodes whose amplitude drops below 0.01 have coherence set to 0.
        """
        for node in self._nodes.values():
            wave = math.cos(self._frequency * time_step + node.phase)
            node.amplitude *= self._decay * abs(wave)
            node.coherence = 1.0 if node.amplitude >= 0.01 else 0.0

    def _interference_score(
        self, a: DigitalThreadNode, b: DigitalThreadNode
    ) -> float:
        """Compute constructive/destructive interference between two nodes.

        Superposition: combined amplitude depends on phase alignment.
        """
        phase_diff = abs(a.phase - b.phase) % (2 * math.pi)
        # Constructive when phases align, destructive when opposed
        interference = math.cos(phase_diff)
        return (a.amplitude + b.amplitude) * (1.0 + interference) / 2.0

    # ------------------------------------------------------------------
    # State collapse
    # ------------------------------------------------------------------

    def collapse_state(
        self,
        origin_repo: str,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Collapse the waveform — return the strongest connected repos.

        Returns a ranked list of ``(repo_id, strength)`` tuples.
        """
        connections = self.get_connections(origin_repo)
        scored: Dict[str, float] = {}

        for node in connections:
            peer = (
                node.target_repo
                if node.source_repo == origin_repo
                else node.source_repo
            )
            strength = node.amplitude * node.coherence
            scored[peer] = scored.get(peer, 0.0) + strength

        ranked = sorted(scored.items(), key=lambda t: t[1], reverse=True)
        return ranked[:top_k]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def get_all_nodes(self) -> List[DigitalThreadNode]:
        return list(self._nodes.values())
