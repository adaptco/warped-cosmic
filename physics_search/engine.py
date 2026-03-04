"""Physics Search Engine — game-model-based retrieval using wave mechanics.

Queries are encoded as wave packets and combined via superposition.
Documents are scored by resonance (constructive interference) with
the combined query waveform, enabling multi-faceted cross-domain search.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from config import INTERFERENCE_THRESHOLD, VECTOR_DIMENSIONS
from schemas import KnowledgeEntry, SearchResult
from physics_search.wave_model import WaveFunction, WaveInterference


class PhysicsSearchEngine:
    """Retrieval engine that models search as wave interference.

    Each query is a ``WaveFunction``; multiple queries are superposed.
    Documents are scored by their resonance (cosine similarity with the
    superposed waveform) weighted by interference classification.
    """

    def __init__(self, dimensions: int = VECTOR_DIMENSIONS) -> None:
        self._dimensions = dimensions
        self._index: Dict[str, Tuple[KnowledgeEntry, WaveFunction]] = {}

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_entry(self, entry: KnowledgeEntry) -> None:
        """Add a knowledge entry to the search index."""
        wave = WaveFunction(
            embedding=list(entry.embedding),
            amplitude=1.0,
            phase=0.0,
        )
        self._index[entry.entry_id] = (entry, wave)

    def index_entries(self, entries: Sequence[KnowledgeEntry]) -> int:
        """Bulk-index entries. Returns count indexed."""
        for entry in entries:
            self.index_entry(entry)
        return len(entries)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        queries: List[str],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Multi-query search using wave superposition.

        Each query string is converted to a ``WaveFunction``, then all
        are superposed. Documents are ranked by resonance with the
        combined waveform.
        """
        # Build superposed query wave
        interference = WaveInterference()
        for i, q in enumerate(queries):
            wave = WaveFunction.from_text(
                q,
                dimensions=self._dimensions,
                phase=i * 0.5,  # offset phases for diversity
            )
            interference.add(wave)

        combined = interference.superpose(t=0.0)
        if not combined:
            return []

        itype = interference.classify_interference()

        # Score each indexed document
        scored: List[Tuple[float, float, KnowledgeEntry]] = []
        for entry, doc_wave in self._index.values():
            cos_sim = self._cosine_similarity(combined, doc_wave.embedding)
            resonance = self._resonance_score(cos_sim, itype)
            if cos_sim >= min_score:
                scored.append((cos_sim, resonance, entry))

        scored.sort(key=lambda t: t[0], reverse=True)

        results: List[SearchResult] = []
        for sim, resonance, entry in scored[:top_k]:
            results.append(
                SearchResult(
                    entry_id=entry.entry_id,
                    repo_id=entry.repo_id,
                    content=entry.content,
                    score=sim,
                    resonance=resonance,
                    interference=itype,
                    source=entry.source,
                )
            )
        return results

    def rank_by_resonance(
        self, results: List[SearchResult]
    ) -> List[SearchResult]:
        """Re-rank results by resonance score (interference-weighted)."""
        return sorted(results, key=lambda r: r.resonance, reverse=True)

    def get_eigenstates(
        self, queries: List[str], time_steps: int = 8
    ) -> List[List[float]]:
        """Sample the query eigenstates over time — returns interference
        pattern snapshots as lists of energy values.
        """
        interference = WaveInterference()
        for i, q in enumerate(queries):
            wave = WaveFunction.from_text(
                q,
                dimensions=self._dimensions,
                phase=i * 0.5,
            )
            interference.add(wave)

        period = 2 * math.pi
        dt = period / max(time_steps, 1)
        snapshots: List[List[float]] = []
        for step in range(time_steps):
            t = step * dt
            combined = interference.superpose(t)
            snapshots.append(combined)
        return snapshots

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _resonance_score(similarity: float, interference_type: str) -> float:
        """Weight similarity by interference classification."""
        weights = {
            "constructive": 1.2,
            "mixed": 1.0,
            "destructive": 0.6,
        }
        return similarity * weights.get(interference_type, 1.0)

    @property
    def index_size(self) -> int:
        return len(self._index)
