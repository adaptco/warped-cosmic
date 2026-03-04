"""Wave Model — query representation as wave packets in the vector space.

Implements superposition, constructive / destructive interference, and
phase matching for the physics-based search engine.
"""

from __future__ import annotations

import hashlib
import math
from typing import List, Sequence

from config import PHASE_RESOLUTION, VECTOR_DIMENSIONS, WAVE_FREQUENCY


class WaveFunction:
    """Represents a query or document as a wave packet in vector space.

    The wave function encodes direction (embedding), amplitude (relevance
    weight), and phase (angular offset) — enabling superposition when
    multiple queries are combined.
    """

    def __init__(
        self,
        embedding: List[float],
        amplitude: float = 1.0,
        phase: float = 0.0,
        frequency: float = WAVE_FREQUENCY,
    ) -> None:
        self.embedding = embedding
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency

    @classmethod
    def from_text(
        cls,
        text: str,
        dimensions: int = VECTOR_DIMENSIONS,
        amplitude: float = 1.0,
        phase: float = 0.0,
    ) -> "WaveFunction":
        """Create a wave function from raw text via deterministic hashing."""
        digest = hashlib.sha256(text.encode()).hexdigest()
        raw = [
            int(digest[i : i + 2], 16) / 255.0
            for i in range(0, min(len(digest), dimensions * 2), 2)
        ]
        while len(raw) < dimensions:
            raw.append(0.0)
        norm = math.sqrt(sum(v * v for v in raw)) or 1.0
        emb = [v / norm for v in raw[:dimensions]]
        return cls(emb, amplitude, phase)

    def evaluate(self, t: float = 0.0) -> List[float]:
        """Evaluate the wave at time *t* → amplitude-modulated embedding."""
        mod = self.amplitude * math.cos(self.frequency * t + self.phase)
        return [v * mod for v in self.embedding]

    @property
    def energy(self) -> float:
        """Wave energy ∝ amplitude²."""
        return self.amplitude ** 2


class WaveInterference:
    """Combines multiple wave functions via superposition.

    Constructive interference amplifies aligned components;
    destructive interference suppresses misaligned ones.
    """

    def __init__(self) -> None:
        self._waves: List[WaveFunction] = []

    def add(self, wave: WaveFunction) -> None:
        self._waves.append(wave)

    def superpose(self, t: float = 0.0) -> List[float]:
        """Superpose all waves at time *t* → combined embedding."""
        if not self._waves:
            return []
        dim = len(self._waves[0].embedding)
        result = [0.0] * dim
        for wave in self._waves:
            evaluated = wave.evaluate(t)
            for i in range(min(dim, len(evaluated))):
                result[i] += evaluated[i]
        # Normalize
        norm = math.sqrt(sum(v * v for v in result)) or 1.0
        return [v / norm for v in result]

    def interference_pattern(
        self, steps: int = PHASE_RESOLUTION
    ) -> List[float]:
        """Sample the interference pattern over one period.

        Returns a list of total-energy values at each time step.
        """
        period = (2 * math.pi / WAVE_FREQUENCY) if WAVE_FREQUENCY else 1.0
        dt = period / max(steps, 1)
        energies: List[float] = []
        for i in range(steps):
            t = i * dt
            combined = self.superpose(t)
            energy = sum(v * v for v in combined)
            energies.append(energy)
        return energies

    def classify_interference(self, t: float = 0.0) -> str:
        """Classify the interference at time *t*.

        Returns ``"constructive"``, ``"destructive"``, or ``"mixed"``.
        """
        if len(self._waves) < 2:
            return "constructive"

        combined = self.superpose(t)
        combined_energy = sum(v * v for v in combined)
        sum_individual = sum(w.energy for w in self._waves)

        if combined_energy > sum_individual * 0.9:
            return "constructive"
        elif combined_energy < sum_individual * 0.3:
            return "destructive"
        return "mixed"

    @property
    def wave_count(self) -> int:
        return len(self._waves)

    @property
    def total_energy(self) -> float:
        return sum(w.energy for w in self._waves)
