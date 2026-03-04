"""Waveform Runtime — middleware that acts as a waveform for the vector space.

Models the runtime environment as a quantum-inspired state space.
Prompts are processed as wave states that can be superposed, measured,
and collapsed into grounded observables for the language transformer.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional

from config import VECTOR_DIMENSIONS, WAVE_DECAY, WAVE_FREQUENCY
from schemas import WaveState
from middleware.vector_space import AgentVectorSpace
from physics_search.wave_model import WaveFunction, WaveInterference


class WaveformRuntime:
    """Middleware runtime modelled as a waveform in the vector space.

    Processes prompts as wave states, grounds transformer tokens to
    vector coordinates, and emits collapsed observables for downstream
    agents.
    """

    def __init__(
        self,
        dimensions: int = VECTOR_DIMENSIONS,
        frequency: float = WAVE_FREQUENCY,
        decay: float = WAVE_DECAY,
    ) -> None:
        self._dimensions = dimensions
        self._frequency = frequency
        self._decay = decay
        self._space = AgentVectorSpace(dimensions)
        self._states: Dict[str, WaveState] = {}
        self._time: float = 0.0

    @property
    def vector_space(self) -> AgentVectorSpace:
        return self._space

    # ------------------------------------------------------------------
    # State processing
    # ------------------------------------------------------------------

    def process_state(self, prompt: str, label: str = "") -> WaveState:
        """Convert a prompt into a WaveState in the vector space.

        The prompt is embedded, registered in the vector space, and
        wrapped in a ``WaveState`` with amplitude/phase metadata.
        """
        label = label or f"state-{uuid.uuid4().hex[:8]}"
        embedding = self._space.embed(label, prompt)

        wave = WaveFunction(
            embedding=embedding,
            amplitude=1.0,
            phase=self._time,
            frequency=self._frequency,
        )
        evaluated = wave.evaluate(self._time)
        energy = wave.energy

        state = WaveState(
            amplitudes=[wave.amplitude],
            phases=[wave.phase],
            dimensions=self._dimensions,
            energy=energy,
            observable=label,
        )
        self._states[state.state_id] = state
        return state

    def collapse_to_prompt(self, state_id: str) -> str:
        """Collapse a wave state into a grounded prompt string.

        Returns a deterministic observable description based on the
        state's vector-space coordinates.
        """
        state = self._states.get(state_id)
        if state is None:
            return ""

        state.collapsed = True

        # Build grounded prompt from the state's observable label
        label = state.observable or ""
        vec = self._space.get_vector(label)
        if vec is None:
            return f"[collapsed:{label}]"

        # Find nearest neighbours to enrich context
        neighbours = self._space.nearest(label, top_k=3)
        context_parts = [f"@{label}"]
        for name, dist in neighbours:
            context_parts.append(f"+{name}(d={dist:.3f})")

        return " ".join(context_parts)

    # ------------------------------------------------------------------
    # Superposition
    # ------------------------------------------------------------------

    def superpose_states(self, state_ids: List[str]) -> WaveState:
        """Superpose multiple wave states into a combined state."""
        interference = WaveInterference()

        for sid in state_ids:
            st = self._states.get(sid)
            if st is None:
                continue
            label = st.observable or ""
            vec = self._space.get_vector(label)
            if vec is None:
                continue
            amp = st.amplitudes[0] if st.amplitudes else 1.0
            phase = st.phases[0] if st.phases else 0.0
            interference.add(WaveFunction(vec, amp, phase))

        combined = interference.superpose(self._time)
        if combined:
            new_label = f"super-{uuid.uuid4().hex[:8]}"
            self._space.embed_vector(new_label, combined)
        else:
            new_label = "empty"

        combined_state = WaveState(
            amplitudes=[1.0],
            phases=[self._time],
            dimensions=self._dimensions,
            energy=interference.total_energy,
            observable=new_label,
        )
        self._states[combined_state.state_id] = combined_state
        return combined_state

    # ------------------------------------------------------------------
    # Observable emission
    # ------------------------------------------------------------------

    def emit_observable(self, state_id: str) -> Dict[str, Any]:
        """Emit a measurement observable for a given state.

        Returns a dictionary representing the collapsed measurement
        that can be consumed by downstream agents.
        """
        state = self._states.get(state_id)
        if state is None:
            return {"error": "state_not_found"}

        label = state.observable or ""
        vec = self._space.get_vector(label)

        return {
            "state_id": state.state_id,
            "observable": label,
            "collapsed": state.collapsed,
            "energy": state.energy,
            "dimensions": state.dimensions,
            "vector_norm": math.sqrt(sum(v * v for v in vec))
            if vec
            else 0.0,
            "timestamp": state.timestamp.isoformat(),
        }

    # ------------------------------------------------------------------
    # Time evolution
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> None:
        """Advance the runtime clock, decaying all active states."""
        self._time += dt
        for state in self._states.values():
            if not state.collapsed:
                state.energy *= self._decay
                if state.amplitudes:
                    state.amplitudes[0] *= self._decay

    @property
    def active_states(self) -> int:
        return sum(1 for s in self._states.values() if not s.collapsed)

    @property
    def current_time(self) -> float:
        return self._time
