"""Configuration for the Digital Brain agent system."""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Vector / Embedding
# ---------------------------------------------------------------------------
VECTOR_DIMENSIONS: int = int(os.getenv("BRAIN_VECTOR_DIM", "32"))
EMBEDDING_MODEL: str = os.getenv(
    "BRAIN_EMBEDDING_MODEL", "deterministic-hash"
)

# ---------------------------------------------------------------------------
# Wave / Physics Parameters
# ---------------------------------------------------------------------------
WAVE_FREQUENCY: float = float(os.getenv("BRAIN_WAVE_FREQ", "1.0"))
WAVE_DECAY: float = float(os.getenv("BRAIN_WAVE_DECAY", "0.95"))
PHASE_RESOLUTION: int = int(os.getenv("BRAIN_PHASE_RES", "64"))
INTERFERENCE_THRESHOLD: float = float(
    os.getenv("BRAIN_INTERFERENCE_THRESH", "0.3")
)

# ---------------------------------------------------------------------------
# Swarm / Orchestrator
# ---------------------------------------------------------------------------
MAX_SWARM_AGENTS: int = int(os.getenv("BRAIN_MAX_AGENTS", "8"))
MAX_RETRIES: int = int(os.getenv("BRAIN_MAX_RETRIES", "3"))
SWARM_TICK_MS: int = int(os.getenv("BRAIN_SWARM_TICK_MS", "100"))

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
MCP_SERVER_NAME: str = os.getenv("BRAIN_MCP_NAME", "DigitalBrain")
MCP_HOST: str = os.getenv("BRAIN_MCP_HOST", "127.0.0.1")
MCP_PORT: int = int(os.getenv("BRAIN_MCP_PORT", "8100"))

# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------
DEFAULT_BRANCH: str = os.getenv("BRAIN_DEFAULT_BRANCH", "main")
COMMIT_PREFIX: str = os.getenv("BRAIN_COMMIT_PREFIX", "brain:")
