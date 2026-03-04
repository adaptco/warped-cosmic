"""Tests for the waveform middleware: WaveformRuntime and AgentVectorSpace."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from middleware.vector_space import AgentVectorSpace
from middleware.wave_runtime import WaveformRuntime


# =====================================================================
# AgentVectorSpace tests
# =====================================================================

class TestAgentVectorSpace:
    def test_embed_and_retrieve(self):
        space = AgentVectorSpace()
        vec = space.embed("test-point", "hello world")
        assert len(vec) == 32
        assert space.point_count == 1
        retrieved = space.get_vector("test-point")
        assert retrieved == vec

    def test_cosine_similarity_identical(self):
        space = AgentVectorSpace()
        space.embed("a", "same text")
        space.embed("b", "same text")
        sim = space.cosine_similarity("a", "b")
        assert abs(sim - 1.0) < 0.001

    def test_measure_distance(self):
        space = AgentVectorSpace()
        space.embed("x", "alpha")
        space.embed("y", "beta")
        dist = space.measure_distance("x", "y")
        assert dist > 0.0

    def test_measure_distance_missing(self):
        space = AgentVectorSpace()
        space.embed("x", "alpha")
        dist = space.measure_distance("x", "missing")
        assert dist == float("inf")

    def test_project(self):
        space = AgentVectorSpace()
        space.embed("a", "projection source")
        space.embed("b", "projection target")
        projected, scalar = space.project("a", "b")
        assert len(projected) == 32
        assert isinstance(scalar, float)

    def test_nearest(self):
        space = AgentVectorSpace()
        space.embed("center", "the center point")
        space.embed("near", "the center nearby point")
        space.embed("far", "completely different unrelated text xyz")

        neighbours = space.nearest("center", top_k=2)
        assert len(neighbours) == 2
        assert neighbours[0][0] in ("near", "far")

    def test_embed_vector_pads(self):
        space = AgentVectorSpace(dimensions=8)
        space.embed_vector("short", [1.0, 2.0])
        vec = space.get_vector("short")
        assert vec is not None
        assert len(vec) == 8


# =====================================================================
# WaveformRuntime tests
# =====================================================================

class TestWaveformRuntime:
    def test_process_state(self):
        rt = WaveformRuntime()
        state = rt.process_state("test prompt")
        assert state.dimensions == 32
        assert not state.collapsed
        assert state.observable is not None
        assert rt.active_states == 1

    def test_collapse_to_prompt(self):
        rt = WaveformRuntime()
        state = rt.process_state("collapse me")
        result = rt.collapse_to_prompt(state.state_id)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_collapse_missing_state(self):
        rt = WaveformRuntime()
        result = rt.collapse_to_prompt("nonexistent")
        assert result == ""

    def test_superpose_states(self):
        rt = WaveformRuntime()
        s1 = rt.process_state("first query")
        s2 = rt.process_state("second query")
        combined = rt.superpose_states([s1.state_id, s2.state_id])
        assert combined.energy > 0.0

    def test_emit_observable(self):
        rt = WaveformRuntime()
        state = rt.process_state("observable test")
        obs = rt.emit_observable(state.state_id)
        assert "state_id" in obs
        assert "energy" in obs
        assert obs["collapsed"] is False

    def test_tick_decays_energy(self):
        rt = WaveformRuntime()
        state = rt.process_state("decay test")
        initial_energy = state.energy
        rt.tick(dt=1.0)
        # Energy should decay
        assert state.energy <= initial_energy

    def test_current_time_advances(self):
        rt = WaveformRuntime()
        assert rt.current_time == 0.0
        rt.tick(dt=2.5)
        assert abs(rt.current_time - 2.5) < 0.001
