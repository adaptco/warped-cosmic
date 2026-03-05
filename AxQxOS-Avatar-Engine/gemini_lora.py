"""
AxQxOS Avatar Engine — Gemini LoRA MLOps Pipeline
mlops/gemini_lora.py  |  v1.0.0

LoRA training loop scaffold using Gemini API for
reward-signal fine-tuning of Avatar Engine weights.
"""
from __future__ import annotations

import json
import os
import time
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from pathlib import Path

import google.generativeai as genai

# ── Config ────────────────────────────────────────────────
GEMINI_API_KEY   = os.environ["GEMINI_API_KEY"]
TUNING_MODEL     = os.getenv("TUNING_MODEL",  "models/gemini-1.5-flash-001-tuning")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
OUTPUT_DIR       = Path(os.getenv("LORA_OUTPUT_DIR", "weights/lora"))
RECEIPT_DIR      = Path(os.getenv("RECEIPT_DIR",     "manifests/lora-receipts"))
EMBEDDING_DIM    = int(os.getenv("EMBEDDING_DIM", 1536))

genai.configure(api_key=GEMINI_API_KEY)
log = logging.getLogger("AxQxOS.LoRA")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")


# ── Data models ───────────────────────────────────────────
@dataclass
class LoRAConfig:
    run_id:          str
    base_model:      str   = TUNING_MODEL
    epoch_count:     int   = 5
    batch_size:      int   = 4
    learning_rate:   float = 0.001
    reward_weight:   float = 0.85     # SDE reward signal weight
    avatar_capsule:  str   = "Sol.F1"
    description:     str   = "AxQxOS Avatar LoRA fine-tune"


@dataclass
class TrainingExample:
    text_input:  str
    output:      str
    reward:      float = 1.0          # agent reward signal [0.0–1.0]


@dataclass
class LoRAReceipt:
    schema:       str   = "AxQxOS/LoRAReceipt/v1"
    run_id:       str   = ""
    config:       dict  = field(default_factory=dict)
    status:       str   = "PENDING"
    tuned_model:  Optional[str] = None
    examples_count: int = 0
    epochs_run:   int   = 0
    canonical_hash: str = ""
    started_at:   str   = ""
    completed_at: str   = ""
    error:        Optional[str] = None


# ── LoRA Trainer ──────────────────────────────────────────
class AvatarLoRATrainer:
    """
    Fine-tunes Gemini models on Avatar Engine task examples.
    Produces deterministic, hash-anchored receipts per run.
    """

    def __init__(self, config: LoRAConfig):
        self.config  = config
        self.receipt = LoRAReceipt(
            run_id    = config.run_id,
            config    = asdict(config),
            started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Build training corpus from Avatar task library ─────
    def build_corpus(self, task_library_path: str) -> list[TrainingExample]:
        with open(task_library_path) as f:
            tasks = json.load(f)

        examples = []
        for task in tasks:
            examples.append(TrainingExample(
                text_input = task["prompt"],
                output     = task["completion"],
                reward     = task.get("reward", 1.0),
            ))

        log.info(f"[{self.config.run_id}] Corpus: {len(examples)} examples loaded")
        return examples

    # ── Reward-weighted training data prep ────────────────
    @staticmethod
    def apply_reward_weighting(
        examples: list[TrainingExample],
        threshold: float = 0.5,
    ) -> list[dict]:
        """Filter and weight examples by SDE reward signal."""
        weighted = [
            {"text_input": ex.text_input, "output": ex.output}
            for ex in examples
            if ex.reward >= threshold
        ]
        log.info(f"Reward-filtered: {len(weighted)}/{len(examples)} examples pass threshold {threshold}")
        return weighted

    # ── Launch Gemini tuning job ──────────────────────────
    def train(self, examples: list[TrainingExample]) -> LoRAReceipt:
        weighted = self.apply_reward_weighting(examples)
        self.receipt.examples_count = len(weighted)

        if not weighted:
            self.receipt.status = "FAILED"
            self.receipt.error  = "No examples passed reward threshold"
            self._save_receipt()
            return self.receipt

        log.info(f"[{self.config.run_id}] Launching Gemini tuning job...")

        try:
            operation = genai.create_tuned_model(
                source_model   = self.config.base_model,
                training_data  = weighted,
                id             = f"axqxos-avatar-{self.config.run_id}",
                display_name   = f"AxQxOS-Avatar-{self.config.avatar_capsule}",
                description    = self.config.description,
                epoch_count    = self.config.epoch_count,
                batch_size     = self.config.batch_size,
                learning_rate  = self.config.learning_rate,
            )

            log.info(f"[{self.config.run_id}] Tuning job submitted. Polling...")

            # Poll until complete
            for status in operation.wait_bar():
                log.info(f"  ↳ {status}")

            tuned_model_name = operation.result().name
            log.info(f"[{self.config.run_id}] ✅ Tuned model: {tuned_model_name}")

            self.receipt.tuned_model  = tuned_model_name
            self.receipt.status       = "COMPLETE"
            self.receipt.epochs_run   = self.config.epoch_count

        except Exception as e:
            log.error(f"[{self.config.run_id}] Training failed: {e}")
            self.receipt.status = "FAILED"
            self.receipt.error  = str(e)

        self.receipt.completed_at   = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.receipt.canonical_hash = self._hash_receipt()
        self._save_receipt()
        return self.receipt

    # ── Embed avatar context for RAG ──────────────────────
    def embed_avatar_corpus(self, texts: list[str]) -> list[list[float]]:
        """Generate Gemini embeddings for Avatar RAG index."""
        embeddings = []
        for chunk in self._batch(texts, 100):
            result = genai.embed_content(
                model   = EMBEDDING_MODEL,
                content = chunk,
                task_type = "RETRIEVAL_DOCUMENT",
                title   = f"AxQxOS-{self.config.avatar_capsule}",
            )
            embeddings.extend(result["embedding"] if isinstance(result["embedding"][0], list)
                              else [result["embedding"]])
        log.info(f"Embedded {len(embeddings)} chunks (dim={len(embeddings[0]) if embeddings else 0})")
        return embeddings

    # ── Internal helpers ──────────────────────────────────
    def _hash_receipt(self) -> str:
        payload = json.dumps(asdict(self.receipt), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

    def _save_receipt(self):
        path = RECEIPT_DIR / f"lora-receipt-{self.receipt.run_id}.json"
        with open(path, "w") as f:
            json.dump(asdict(self.receipt), f, indent=2)
        log.info(f"Receipt saved: {path}")

    @staticmethod
    def _batch(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]


# ── CLI entry ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse, uuid

    parser = argparse.ArgumentParser(description="AxQxOS Avatar LoRA Trainer")
    parser.add_argument("--corpus",   required=True, help="Path to task_library.json")
    parser.add_argument("--capsule",  default="Sol.F1", help="Avatar capsule binding")
    parser.add_argument("--epochs",   type=int, default=5)
    parser.add_argument("--lr",       type=float, default=0.001)
    parser.add_argument("--run-id",   default=None)
    args = parser.parse_args()

    run_id = args.run_id or f"lora-{uuid.uuid4().hex[:8]}"
    cfg    = LoRAConfig(
        run_id         = run_id,
        epoch_count    = args.epochs,
        learning_rate  = args.lr,
        avatar_capsule = args.capsule,
    )

    trainer  = AvatarLoRATrainer(cfg)
    examples = trainer.build_corpus(args.corpus)
    receipt  = trainer.train(examples)

    print(json.dumps(asdict(receipt), indent=2))
