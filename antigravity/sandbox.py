"""
AxQxOS Avatar Engine — Antigravity Local Sandbox
antigravity/sandbox.py  |  v1.0.0

Local environment for tuning Avatar Engine weights
using Gemini API reward signals before production push.
Acts as the pre-flight staging layer before LoRA jobs
are submitted to the cloud tuning pipeline.
"""
from __future__ import annotations

import json
import os
import hashlib
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

import google.generativeai as genai

GEMINI_API_KEY  = os.environ["GEMINI_API_KEY"]
SANDBOX_DIR     = Path(os.getenv("ANTIGRAVITY_DIR", ".antigravity"))
REWARD_THRESHOLD = float(os.getenv("REWARD_THRESHOLD", "0.75"))
EVAL_MODEL       = os.getenv("EVAL_MODEL", "gemini-1.5-flash")

genai.configure(api_key=GEMINI_API_KEY)
log = logging.getLogger("AxQxOS.Antigravity")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")


@dataclass
class TuningCandidate:
    prompt:     str
    completion: str
    weight:     float = 1.0   # tunable weight [0.0–2.0]
    reward:     float = 0.0   # Gemini-evaluated reward
    status:     str   = "UNSCORED"


@dataclass
class SandboxSession:
    schema:      str   = "AxQxOS/AntigravitySession/v1"
    session_id:  str   = ""
    capsule:     str   = ""
    candidates:  list  = field(default_factory=list)
    passed:      int   = 0
    failed:      int   = 0
    total:       int   = 0
    mean_reward: float = 0.0
    hash:        str   = ""
    timestamp:   str   = ""
    promoted:    bool  = False


class AntigravitySandbox:
    """
    Local weight-tuning sandbox using Gemini as a reward evaluator.

    Workflow:
      1. Load candidates (prompt/completion pairs)
      2. Score each via Gemini reward model call
      3. Apply gradient-free weight updates (reward weighting)
      4. Emit pass/fail corpus for LoRA promotion
      5. Save signed session receipt
    """

    REWARD_SYSTEM = """You are a reward evaluator for the AxQxOS Avatar Engine.
Score the following prompt/completion pair on a scale of 0.0 to 1.0 based on:
- Correctness and completeness (40%)
- Adherence to ADK v0 surface contract (30%)
- Code quality and determinism (20%)
- Avatar capsule alignment (10%)

Respond with ONLY a JSON object: {"reward": <float>, "rationale": "<string>"}"""

    def __init__(self, capsule: str = "Sol.F1", session_id: Optional[str] = None):
        import uuid
        self.capsule    = capsule
        self.session_id = session_id or f"ag-{uuid.uuid4().hex[:8]}"
        self.candidates: list[TuningCandidate] = []
        self.model      = genai.GenerativeModel(EVAL_MODEL)
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        log.info(f"[Antigravity] Session: {self.session_id} | Capsule: {capsule}")

    # ── Load corpus ───────────────────────────────────────
    def load(self, path: str) -> "AntigravitySandbox":
        with open(path) as f:
            data = json.load(f)
        self.candidates = [TuningCandidate(**d) for d in data]
        log.info(f"Loaded {len(self.candidates)} candidates from {path}")
        return self

    # ── Score via Gemini reward model ─────────────────────
    def score(self) -> "AntigravitySandbox":
        log.info(f"Scoring {len(self.candidates)} candidates via Gemini...")
        for i, c in enumerate(self.candidates):
            prompt = f"""Prompt: {c.prompt}

Completion:
{c.completion}"""
            try:
                resp   = self.model.generate_content(
                    [{"role": "user", "parts": [self.REWARD_SYSTEM + "\n\n" + prompt]}]
                )
                raw    = resp.text.strip()
                parsed = json.loads(raw)
                c.reward = float(parsed.get("reward", 0.0))
                c.status = "SCORED"
                log.info(f"  [{i+1}/{len(self.candidates)}] reward={c.reward:.3f}")
            except Exception as e:
                log.warning(f"  [{i+1}] Score failed: {e}")
                c.reward = 0.0
                c.status = "SCORE_ERROR"
            time.sleep(0.1)  # rate-limit guard
        return self

    # ── Apply reward-driven weight update ─────────────────
    def tune_weights(self) -> "AntigravitySandbox":
        """
        Gradient-free weight update: scale candidate weight
        by reward signal. Acts as a pre-filter before LoRA.
        """
        for c in self.candidates:
            if c.status == "SCORED":
                c.weight = round(c.reward * 2.0, 4)  # map [0,1] → [0,2]
        log.info("Weight tuning applied.")
        return self

    # ── Filter and emit LoRA-ready corpus ─────────────────
    def emit(self, output_path: Optional[str] = None) -> list[dict]:
        passed = [c for c in self.candidates if c.reward >= REWARD_THRESHOLD]
        failed = [c for c in self.candidates if c.reward <  REWARD_THRESHOLD]
        log.info(f"Pass: {len(passed)} | Fail: {len(failed)} | Threshold: {REWARD_THRESHOLD}")

        corpus = [{"text_input": c.prompt, "output": c.completion, "reward": c.reward}
                  for c in passed]

        out = output_path or str(SANDBOX_DIR / f"{self.session_id}-corpus.json")
        with open(out, "w") as f:
            json.dump(corpus, f, indent=2)
        log.info(f"LoRA corpus emitted: {out}")

        # Session receipt
        session = SandboxSession(
            session_id  = self.session_id,
            capsule     = self.capsule,
            candidates  = [asdict(c) for c in self.candidates],
            passed      = len(passed),
            failed      = len(failed),
            total       = len(self.candidates),
            mean_reward = round(sum(c.reward for c in self.candidates) / max(len(self.candidates), 1), 4),
            timestamp   = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        session.hash = hashlib.sha256(
            json.dumps(asdict(session), sort_keys=True).encode()
        ).hexdigest()

        receipt_path = SANDBOX_DIR / f"{self.session_id}-receipt.json"
        with open(receipt_path, "w") as f:
            json.dump(asdict(session), f, indent=2)
        log.info(f"Session receipt: {receipt_path}")

        return corpus

    # ── Full pipeline ─────────────────────────────────────
    def run(self, corpus_path: str, output_path: Optional[str] = None) -> list[dict]:
        return (
            self.load(corpus_path)
                .score()
                .tune_weights()
                .emit(output_path)
        )


# ── CLI entry ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Antigravity Sandbox — Local LoRA pre-filter")
    parser.add_argument("--corpus",  required=True, help="Input candidates JSON")
    parser.add_argument("--output",  default=None,  help="Output corpus JSON path")
    parser.add_argument("--capsule", default="Sol.F1")
    parser.add_argument("--session", default=None)
    args = parser.parse_args()

    sandbox = AntigravitySandbox(capsule=args.capsule, session_id=args.session)
    corpus  = sandbox.run(args.corpus, args.output)
    print(f"\n✅ Antigravity run complete. {len(corpus)} examples ready for LoRA.")
