"""Determinism checks for yield engine outputs."""
from __future__ import annotations

from mlops.yield_engine import QuantumSDEYieldEngine


def test_yield_surface_is_deterministic_for_fixed_run() -> None:
    engine = QuantumSDEYieldEngine()
    a = engine.yield_surface(run_id="determinism-check")
    b = engine.yield_surface(run_id="determinism-check")

    assert a.gamma_yield == b.gamma_yield
    assert a.annihilation["epsilon_0"] == b.annihilation["epsilon_0"]
    assert a.curve[0]["yield_"] == b.curve[0]["yield_"]


def test_separation_matrix_shape() -> None:
    engine = QuantumSDEYieldEngine()
    mat = engine.separation_matrix()
    assert mat.shape[0] == mat.shape[1]
    assert mat.shape[0] >= 8
