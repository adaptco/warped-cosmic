"""
AxQxOS Avatar Engine — Avatar CodeGen Agent
agents/avatar_codegen_agent.py  |  v1.0.0

Production agent for generating embodied Avatar modules
at runtime. Connects to MCP server via WebSocket and
processes AVATAR_CODEGEN task assignments.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Optional

import websockets

from agents.llm_router import default_model_for_target, generate_json, resolve_target

MCP_WS_URL      = os.getenv("MCP_WS_URL",     "ws://localhost:3001")
AGENT_CAPSULE   = os.getenv("AGENT_CAPSULE",   "Sol.F1")
LLM_TARGET      = os.getenv("LLM_TARGET", "gemini")
MODEL_ID        = os.getenv("MODEL_ID") or os.getenv("TUNED_MODEL_ID")
log = logging.getLogger("AxQxOS.AvatarCodeGenAgent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")


AVATAR_SYSTEM_PROMPT = """You are the AxQxOS Avatar CodeGen Agent, bound to capsule {capsule}.

Your task is to generate embodied Avatar runtime modules following the ADK v0 surface contract:
  - capsule: identifies the avatar binding
  - input_artifact: structured task spec
  - transition_request: state machine event
  - output_artifact: generated module code
  - receipt: deterministic hash-anchored metadata
  - block: immutable execution record

Requirements:
  - All code is deterministic and traceable
  - Each output includes a canonical hash
  - Avatar personality and physics are governed by the PRIME_DIRECTIVE
  - Adhere to AxQxOS SDE (signal-driven economics) token model

Return a JSON object with keys: code, module_name, capsule_binding, receipt_hash, dependencies[]
"""


@dataclass
class AvatarArtifact:
    schema:          str = "AxQxOS/AvatarArtifact/v1"
    task_id:         str = ""
    capsule:         str = AGENT_CAPSULE
    module_name:     str = ""
    code:            str = ""
    dependencies:    list = None
    receipt_hash:    str = ""
    generated_at:    str = ""
    model_used:      str = ""

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class AvatarCodeGenAgent:
    """
    Connects to the MCP A2A server as AVATAR_CODEGEN role.
    Processes task assignments and returns generated avatar modules.
    """

    def __init__(self):
        self.agent_id = None
        self.llm_target = resolve_target(LLM_TARGET)
        self.model_id = MODEL_ID or default_model_for_target(self.llm_target)
        self.system_prompt = AVATAR_SYSTEM_PROMPT.format(capsule=AGENT_CAPSULE)
        self.ws = None

    async def connect(self):
        log.info(f"Connecting to MCP: {MCP_WS_URL} (target={self.llm_target}, model={self.model_id})")
        self.ws = await websockets.connect(MCP_WS_URL)

        # Await session init
        raw  = await self.ws.recv()
        init = json.loads(raw)
        self.agent_id = init["agentId"]
        log.info(f"Session: {self.agent_id}")

        # Register role
        await self.ws.send(json.dumps({
            "type":    "REGISTER",
            "role":    "AVATAR_CODEGEN",
            "capsule": AGENT_CAPSULE,
        }))

        ack = json.loads(await self.ws.recv())
        log.info(f"Registered: {ack}")

    async def listen(self):
        log.info("Listening for task assignments...")
        async for raw in self.ws:
            msg = json.loads(raw)

            if msg["type"] == "TASK_ASSIGNED":
                asyncio.create_task(self.handle_task(msg))
            elif msg["type"] == "AGENT_JOINED":
                log.info(f"Agent joined: {msg['agentId']} as {msg['role']}")

    async def handle_task(self, msg: dict):
        task_id = msg["taskId"]
        payload = msg["payload"]
        fmt     = msg.get("format", "json")

        log.info(f"Processing task: {task_id}")

        try:
            artifact = await self.generate_avatar(task_id, payload)
            result   = asdict(artifact)
            if fmt == "yaml":
                import yaml
                result = yaml.dump(result)
            elif fmt == "markdown":
                result = self._to_markdown(artifact)

            await self.ws.send(json.dumps({
                "type":   "TASK_RESULT",
                "taskId": task_id,
                "result": result,
            }))
            log.info(f"Task complete: {task_id}")

        except Exception as e:
            log.error(f"Task failed {task_id}: {e}")
            await self.ws.send(json.dumps({
                "type":   "TASK_RESULT",
                "taskId": task_id,
                "result": {"error": str(e), "task_id": task_id},
            }))

    async def generate_avatar(self, task_id: str, payload: Any) -> AvatarArtifact:
        prompt = f"""TASK_ID: {task_id}

AVATAR SPEC:
{json.dumps(payload, indent=2) if isinstance(payload, dict) else str(payload)}

Generate the complete embodied Avatar runtime module per ADK v0 surface contract.
Return ONLY a valid JSON object with keys: code, module_name, capsule_binding, receipt_hash, dependencies"""

        parsed = await asyncio.to_thread(
            generate_json,
            system_prompt=self.system_prompt,
            user_message=prompt,
            llm_target=self.llm_target,
            model_id=self.model_id,
        )

        artifact = AvatarArtifact(
            task_id      = task_id,
            module_name  = parsed.get("module_name",     f"avatar_{task_id[:8]}"),
            code         = parsed.get("code",            ""),
            dependencies = parsed.get("dependencies",    []),
            model_used   = self.model_id,
            generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # Canonical hash
        content = (artifact.module_name + artifact.code + artifact.generated_at).encode()
        artifact.receipt_hash = hashlib.sha256(content).hexdigest()

        return artifact

    def _to_markdown(self, a: AvatarArtifact) -> str:
        return f"""# Avatar Artifact: {a.module_name}

**Task:** `{a.task_id}`
**Capsule:** `{a.capsule}`
**Hash:** `{a.receipt_hash}`
**Generated:** {a.generated_at}

## Code
```python
{a.code}
```

## Dependencies
{chr(10).join(f"- `{d}`" for d in a.dependencies)}

---
*Canonical truth, attested and replayable.*
"""

    async def run(self):
        await self.connect()
        await self.listen()


# ── Entry ──────────────────────────────────────────────────
if __name__ == "__main__":
    agent = AvatarCodeGenAgent()
    asyncio.run(agent.run())
