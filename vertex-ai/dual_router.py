"""
AxQxOS WHAM Engine — Vertex AI + Codestral Dual Router
vertex-ai/dual_router.py  |  v1.0.0

Routes inference requests between:
  - Google Vertex AI (Gemini 1.5 Pro/Flash) for generation, embeddings, vision
  - Codestral HTTP (Mistral) for A2A agent scaffolding and code synthesis

Modeled as a lattice-aware router: each request carries a worldline token
that determines which API handles the inference.
"""
from __future__ import annotations

import json
import os
import time
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

import httpx
import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part
from vertexai.language_models import TextEmbeddingModel

# ── Config ────────────────────────────────────────────────
VERTEX_PROJECT    = os.environ["VERTEX_PROJECT_ID"]
VERTEX_LOCATION   = os.getenv("VERTEX_LOCATION", "us-central1")
CODESTRAL_API_KEY = os.environ["CODESTRAL_API_KEY"]
CODESTRAL_BASE    = "https://codestral.mistral.ai/v1"

vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
log = logging.getLogger("AxQxOS.DualRouter")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")


class RouterBackend(str, Enum):
    GEMINI_PRO      = "gemini-1.5-pro"
    GEMINI_FLASH    = "gemini-1.5-flash"
    GEMINI_EMBED    = "text-embedding-004"
    CODESTRAL       = "codestral-latest"


@dataclass
class RouterRequest:
    task_id:    str
    agent:      str           # CELINE | SPRYTE | ECHO | GLOH | LUMA | DOT
    task_type:  str           # generate | embed | code | vision
    prompt:     str
    context:    dict = field(default_factory=dict)
    format:     str  = "json"
    backend:    Optional[RouterBackend] = None


@dataclass
class RouterReceipt:
    schema:       str  = "AxQxOS/RouterReceipt/v1"
    task_id:      str  = ""
    agent:        str  = ""
    backend_used: str  = ""
    tokens_in:    int  = 0
    tokens_out:   int  = 0
    latency_ms:   float= 0.0
    output:       Any  = None
    canonical_hash: str = ""
    timestamp:    str  = ""


# ── Routing table: agent → preferred backend ──────────────
AGENT_ROUTING = {
    "CELINE": RouterBackend.GEMINI_PRO,    # Orchestrator → full reasoning
    "SPRYTE": RouterBackend.CODESTRAL,     # UI Codegen → Codestral code synthesis
    "ECHO":   RouterBackend.GEMINI_EMBED,  # RAG → embeddings
    "GLOH":   RouterBackend.GEMINI_FLASH,  # Token econ → fast inference
    "LUMA":   RouterBackend.GEMINI_PRO,    # Render → vision + generation
    "DOT":    RouterBackend.CODESTRAL,     # Witness/QA → code diff + PR analysis
}


class WHAMDualRouter:
    """
    Dual-backend router for the WHAM Engine.
    Routes requests via worldline token → Gemini or Codestral.
    All receipts are hash-anchored for ledger integrity.
    """

    def __init__(self):
        self.gemini_pro   = GenerativeModel("gemini-1.5-pro")
        self.gemini_flash = GenerativeModel("gemini-1.5-flash")
        self.embed_model  = TextEmbeddingModel.from_pretrained("text-embedding-004")
        self.http         = httpx.Client(timeout=60.0)
        self.ledger: list[RouterReceipt] = []

    # ── Route request ─────────────────────────────────────
    def route(self, req: RouterRequest) -> RouterReceipt:
        backend = req.backend or AGENT_ROUTING.get(req.agent, RouterBackend.GEMINI_FLASH)
        start   = time.time()

        log.info(f"[Router] {req.agent} → {backend} | task: {req.task_id}")

        if backend == RouterBackend.GEMINI_EMBED:
            output = self._gemini_embed(req)
        elif backend in (RouterBackend.GEMINI_PRO, RouterBackend.GEMINI_FLASH):
            output = self._gemini_generate(req, backend)
        elif backend == RouterBackend.CODESTRAL:
            output = self._codestral_generate(req)
        else:
            raise ValueError(f"Unknown backend: {backend}")

        latency = (time.time() - start) * 1000

        receipt = RouterReceipt(
            task_id      = req.task_id,
            agent        = req.agent,
            backend_used = backend.value,
            latency_ms   = round(latency, 2),
            output       = output,
            timestamp    = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        receipt.canonical_hash = hashlib.sha256(
            json.dumps(asdict(receipt), sort_keys=True, default=str).encode()
        ).hexdigest()

        self.ledger.append(receipt)
        log.info(f"[Router] ✓ {req.agent} | {latency:.0f}ms | hash:{receipt.canonical_hash[:8]}")
        return receipt

    # ── Gemini generate ───────────────────────────────────
    def _gemini_generate(self, req: RouterRequest, backend: RouterBackend) -> dict:
        model = self.gemini_pro if backend == RouterBackend.GEMINI_PRO else self.gemini_flash

        system_ctx = f"""You are {req.agent}, an AxQxOS WHAM Engine Avatar Agent.
Capsule: {self._capsule_for(req.agent)}
Task type: {req.task_type}
Format: {req.format}
Context: {json.dumps(req.context)}

Return output as {req.format.upper()}. For JSON: valid JSON only, no markdown fences."""

        response = model.generate_content(
            [Content(role="user", parts=[Part.from_text(system_ctx + "\n\n" + req.prompt)])]
        )

        raw = response.text
        if req.format == "json":
            try:
                raw = raw.strip().lstrip("```json").rstrip("```").strip()
                return json.loads(raw)
            except Exception:
                return {"raw": raw}
        return {"text": raw}

    # ── Gemini embeddings ─────────────────────────────────
    def _gemini_embed(self, req: RouterRequest) -> dict:
        texts = [req.prompt] if isinstance(req.prompt, str) else req.prompt
        embeddings = self.embed_model.get_embeddings(
            texts,
            task_type="RETRIEVAL_DOCUMENT",
        )
        return {
            "embeddings": [e.values for e in embeddings],
            "dim": len(embeddings[0].values) if embeddings else 0,
        }

    # ── Codestral generate ────────────────────────────────
    def _codestral_generate(self, req: RouterRequest) -> dict:
        system = f"""You are {req.agent}, an AxQxOS A2A coding agent.
Capsule: {self._capsule_for(req.agent)}
Task: {req.task_type}
Return ONLY production-grade code. No preamble. No explanation after code."""

        resp = self.http.post(
            f"{CODESTRAL_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {CODESTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "codestral-latest",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": req.prompt},
                ],
                "temperature": 0.05,
                "max_tokens":  4096,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "code":         data["choices"][0]["message"]["content"],
            "tokens_in":    data["usage"]["prompt_tokens"],
            "tokens_out":   data["usage"]["completion_tokens"],
        }

    @staticmethod
    def _capsule_for(agent: str) -> str:
        CAPSULES = {
            "CELINE": "Cap.Zul",
            "SPRYTE": "Qube™",
            "ECHO":   "Echo.Mesh",
            "GLOH":   "LQQM",
            "LUMA":   "Sol.F1",
            "DOT":    "Glyph.Trace",
        }
        return CAPSULES.get(agent, "unknown")

    def dump_ledger(self, path: str = "manifests/router-ledger.json"):
        import os; os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump([asdict(r) for r in self.ledger], f, indent=2, default=str)
        log.info(f"Router ledger saved: {path} ({len(self.ledger)} entries)")
