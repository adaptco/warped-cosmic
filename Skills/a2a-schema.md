# A2A Protocol JSON Schema Reference

## Task Node (full)
```json
{
  "task_id": "T-001",
  "name": "string",
  "description": "string",
  "inputs": ["T-000" | "artifact:id"],
  "outputs": ["artifact:id"],
  "agent_card": "agents/<Name>.md",
  "rasic_role": "R" | "A" | "S" | "I" | "C",
  "boo_binding": "Celine|Spryte|Echo|Gloh|Luma|Dot|null",
  "llm_target": "claude|openai|gemini|ollama|any",
  "model_id": "claude-sonnet-4-20250514|gpt-4o|gemini-2.0-flash|...",
  "mcp_server": "https://...|null",
  "webhook_out": "https://...|null",
  "github_action": "workflow-name.yml",
  "retry_policy": { "max_attempts": 3, "backoff_seconds": 5 },
  "timeout_seconds": 300,
  "status": "pending|running|complete|failed",
  "created_at": "ISO8601",
  "completed_at": "ISO8601|null"
}
```

## Task Graph Root
```json
{
  "schema_version": "a2a/1.0",
  "project": "project-name",
  "goal": "one-sentence goal",
  "created_at": "ISO8601",
  "tasks": [ <TaskNode>, ... ],
  "artifacts": [
    {
      "artifact_id": "artifact:id",
      "type": "code|doc|data|config|receipt",
      "path": "artifacts/<task_id>/<filename>",
      "produced_by": "T-001",
      "consumed_by": ["T-002"]
    }
  ]
}
```

## Webhook Envelope
```json
{
  "envelope_version": "1.0",
  "task_id": "T-001",
  "from_agent": "AgentName",
  "to_agent": "AgentName",
  "llm_hop": "claude → openai",
  "mcp_route": "echo-relay",
  "payload": {
    "artifact_id": "artifact:id",
    "data": "string|object"
  },
  "timestamp": "ISO8601",
  "signature": "Ed25519-base64|null"
}
```

## Luma Receipt
```json
{
  "receipt_id": "RCP-001",
  "task_id": "T-001",
  "attested_by": "Luma",
  "status": "pass|fail|warn",
  "assertions": [
    { "check": "output_exists", "result": true },
    { "check": "schema_valid", "result": true },
    { "check": "webhook_fired", "result": true }
  ],
  "timestamp": "ISO8601",
  "signature": "Ed25519-base64|null"
}
```
