"""Agent Vector Space — runtime vector coordinate system for grounding.

Maps prompt tokens and agent states into a shared vector coordinate
system enabling distance measurement, projection, and embedding.
"""

from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Optional, Sequence, Tuple

from config import VECTOR_DIMENSIONS


class AgentVectorSpace:
    """Runtime vector space model for agent state propagation.

    Provides a shared coordinate system where prompt tokens, knowledge
    entries, and agent states can coexist and be compared.
    """

    def __init__(self, dimensions: int = VECTOR_DIMENSIONS) -> None:
        self._dimensions = dimensions
        self._points: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def embed(self, label: str, text: str) -> List[float]:
        """Embed text into the vector space and register it under *label*."""
        vec = self._deterministic_embedding(text)
        self._points[label] = vec
        return vec

    def embed_vector(self, label: str, vector: List[float]) -> None:
        """Register a pre-computed vector under *label*."""
        # Pad / truncate
        vec = list(vector)
        while len(vec) < self._dimensions:
            vec.append(0.0)
        vec = vec[: self._dimensions]
        self._points[label] = vec

    # ------------------------------------------------------------------
    # Measurement
    # ------------------------------------------------------------------

    def measure_distance(self, label_a: str, label_b: str) -> float:
        """Euclidean distance between two named points."""
        a = self._points.get(label_a)
        b = self._points.get(label_b)
        if a is None or b is None:
            return float("inf")
        return math.sqrt(
            sum((x - y) ** 2 for x, y in zip(a, b))
        )

    def cosine_similarity(self, label_a: str, label_b: str) -> float:
        """Cosine similarity between two named points."""
        a = self._points.get(label_a)
        b = self._points.get(label_b)
        if a is None or b is None:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (na * nb)

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------

    def project(
        self, label: str, onto_label: str
    ) -> Tuple[List[float], float]:
        """Project *label* onto *onto_label*.

        Returns the projected vector and the scalar projection magnitude.
        """
        a = self._points.get(label)
        b = self._points.get(onto_label)
        if a is None or b is None:
            return [0.0] * self._dimensions, 0.0

        dot = sum(x * y for x, y in zip(a, b))
        b_norm_sq = sum(y * y for y in b) or 1.0
        scalar = dot / b_norm_sq
        projected = [scalar * y for y in b]
        return projected, scalar

    # ------------------------------------------------------------------
    # Neighbourhood
    # ------------------------------------------------------------------

    def nearest(
        self, label: str, top_k: int = 5, exclude_self: bool = True
    ) -> List[Tuple[str, float]]:
        """Find the *top_k* nearest neighbours to *label*."""
        ref = self._points.get(label)
        if ref is None:
            return []

        scored: List[Tuple[str, float]] = []
        for name, vec in self._points.items():
            if exclude_self and name == label:
                continue
            dist = math.sqrt(
                sum((x - y) ** 2 for x, y in zip(ref, vec))
            )
            scored.append((name, dist))

        scored.sort(key=lambda t: t[1])
        return scored[:top_k]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _deterministic_embedding(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode()).hexdigest()
        raw = [
            int(digest[i : i + 2], 16) / 255.0
            for i in range(0, min(len(digest), self._dimensions * 2), 2)
        ]
        while len(raw) < self._dimensions:
            raw.append(0.0)
        norm = math.sqrt(sum(v * v for v in raw)) or 1.0
        return [v / norm for v in raw[: self._dimensions]]

    @property
    def point_count(self) -> int:
        return len(self._points)

    def get_vector(self, label: str) -> Optional[List[float]]:
        return self._points.get(label)
