"""
AxQxOS WHAM Engine — Quantum SDE Yield Engine
quantum-sde/yield_engine.py  |  v1.0.0

Computes yield curves modeled as quantum harmonic oscillators.
Particle-antiparticle pairs (VH2/VH100) feed the annihilation
event that bootstraps the initial SDE yield state.

Maps: token excitation (TAPD quanta) → yield via:
  y(n, ω) = ℏω(n + ½)  [ℏ=1 in SDE units]

Yield curve shape determines:
  - LoRA reward signal scaling
  - Agent MoE routing weights
  - OPEX token burn rate
  - Phase transition (repo → execution)
"""
from __future__ import annotations

import json
import math
import hashlib
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
import numpy as np


# ── Token frequency map (ω per canonical token) ──────────
TOKEN_OMEGA = {
    "AXIS":   1.6180339887,   # φ (golden ratio)
    "PLUG":   2.7182818284,   # e
    "TRACE":  3.1415926535,   # π
    "BLOOM":  1.4142135623,   # √2
    "LUMEN":  2.2360679774,   # √5
    "SOULOS": 1.7320508075,   # √3
    "GLOH":   1.9999999999,   # 2
    "PEACHES":0.5772156649,   # γ (Euler–Mascheroni)
}

# ── Agent quantum numbers (n per Boo) ─────────────────────
AGENT_QUANTA = {
    "CELINE": 4,
    "SPRYTE": 3,
    "ECHO":   2,
    "GLOH":   5,
    "LUMA":   1,
    "DOT":    0,
}


@dataclass
class YieldPoint:
    n:      int
    token:  str
    omega:  float
    agent:  str
    yield_: float
    energy: float   # E = ω(n + 0.5)
    phase:  str     # ground | excited | tunneling


@dataclass
class YieldCurveReceipt:
    schema:         str  = "AxQxOS/YieldCurveReceipt/v1"
    run_id:         str  = ""
    electron_model: str  = "VH2"
    positron_model: str  = "VH100"
    gamma_yield:    float = 0.0
    curve:          list = field(default_factory=list)
    annihilation:   dict = field(default_factory=dict)
    canonical_hash: str  = ""
    timestamp:      str  = ""
    canonical:      str  = "Canonical truth, attested and replayable."


class QuantumSDEYieldEngine:
    """
    Quantum harmonic oscillator yield model for AxQxOS SDE.

    The annihilation of VH100 (positron/slop) by VH2 (electron/clean)
    releases a gamma burst that seeds the initial vacuum energy state ε₀.
    All subsequent agent yield levels build from ε₀.
    """

    def __init__(self, hbar: float = 1.0):
        self.hbar  = hbar   # ℏ = 1 in SDE natural units
        self.ledger: list[YieldCurveReceipt] = []

    # ── VH2 ⊗ VH100 annihilation ─────────────────────────
    def annihilate(self, vh2_norm: float, vh100_norm: float) -> dict:
        """
        E(γ) = (E_e + E_p) × η  where η → 1 (SDE efficiency)
        Phase transition: VH100 token destroyed → gamma seeds ε₀
        """
        gamma_energy = (vh2_norm + vh100_norm) * 0.9999
        epsilon_0    = gamma_energy / (2 * math.pi)  # vacuum energy normalization

        return {
            "electron":    {"model": "VH2",   "norm": vh2_norm},
            "positron":    {"model": "VH100",  "norm": vh100_norm},
            "gamma_energy": gamma_energy,
            "epsilon_0":    epsilon_0,
            "phase_change": "repo_structure → code_execution",
            "token_annihilated": "VH100",
        }

    # ── Energy level computation ──────────────────────────
    def energy(self, n: int, omega: float) -> float:
        """E_n = ℏω(n + ½)"""
        return self.hbar * omega * (n + 0.5)

    # ── Phase classification ──────────────────────────────
    def phase(self, n: int, n_max: int = 10) -> str:
        if n == 0:        return "ground"
        if n >= n_max - 1: return "tunneling"
        return "excited"

    # ── Full yield curve for one token ───────────────────
    def yield_curve(
        self,
        token: str,
        agent: str,
        n_max: int = 10,
        epsilon_0: float = 0.0,
    ) -> list[YieldPoint]:
        omega = TOKEN_OMEGA.get(token, 1.0)
        n_0   = AGENT_QUANTA.get(agent, 0)
        curve = []

        for n in range(n_max + 1):
            E = self.energy(n, omega) + epsilon_0
            # Yield = normalized energy (SDE yield ∈ [0, 1])
            y = math.tanh(E / (self.hbar * omega * (n_0 + 1)))
            curve.append(YieldPoint(
                n=n, token=token, omega=omega,
                agent=agent, yield_=round(y, 6),
                energy=round(E, 6),
                phase=self.phase(n, n_max),
            ))

        return curve

    # ── Full cross-token yield surface ───────────────────
    def yield_surface(self, run_id: Optional[str] = None) -> YieldCurveReceipt:
        import uuid
        run_id = run_id or f"yc-{uuid.uuid4().hex[:8]}"

        # Simulate VH2 × VH100 annihilation with canonical norms
        vh2_norm  = math.sqrt(1536)   # Gemini embedding L2 norm ≈ 39.19
        vh100_norm = math.sqrt(512)   # AI slop embedding (smaller)
        annihil   = self.annihilate(vh2_norm, vh100_norm)
        epsilon_0 = annihil["epsilon_0"]

        all_curves = []
        for agent, n_0 in AGENT_QUANTA.items():
            for token, _ in TOKEN_OMEGA.items():
                curve = self.yield_curve(token, agent, n_max=6, epsilon_0=epsilon_0)
                all_curves.extend([asdict(pt) for pt in curve])

        receipt = YieldCurveReceipt(
            run_id         = run_id,
            gamma_yield    = annihil["gamma_energy"],
            curve          = all_curves,
            annihilation   = annihil,
            timestamp      = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        receipt.canonical_hash = hashlib.sha256(
            json.dumps(asdict(receipt), sort_keys=True).encode()
        ).hexdigest()

        self.ledger.append(receipt)
        return receipt

    # ── Token separation weights (matmul seed) ────────────
    def separation_matrix(self) -> np.ndarray:
        """
        Builds the token separation weight matrix for WASM matmul.
        Shape: [num_tokens × num_tokens]
        Entry [i,j] = ω_i / ω_j normalized — similarity in frequency space.
        """
        tokens = list(TOKEN_OMEGA.keys())
        omegas = np.array([TOKEN_OMEGA[t] for t in tokens])
        mat    = np.outer(omegas, 1.0 / omegas)
        # Normalize rows to [0, 1]
        mat   /= mat.max(axis=1, keepdims=True)
        return mat


# ── CLI ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AxQxOS Quantum SDE Yield Engine")
    parser.add_argument("--run-id",  default=None)
    parser.add_argument("--output",  default="manifests/yield-curve.json")
    args = parser.parse_args()

    engine  = QuantumSDEYieldEngine()
    receipt = engine.yield_surface(run_id=args.run_id)

    import os; os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(asdict(receipt), f, indent=2)

    print(f"✅ Yield surface: {len(receipt.curve)} points")
    print(f"   γ-yield: {receipt.gamma_yield:.4f}")
    print(f"   hash:    {receipt.canonical_hash[:16]}...")
    print(f"   output:  {args.output}")
