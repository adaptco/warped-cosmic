// ============================================================
// AxQxOS Avatar Engine — A2A Arbitration Layer
// mcp-server/a2a-arbiter.js  |  v1.0.0
// Codestral-powered scaffolding & task routing
// ============================================================

export class ArbitrationLayer {
  constructor(apiKey, baseUrl) {
    this.apiKey  = apiKey;
    this.baseUrl = baseUrl;
    this.model   = "codestral-latest";
  }

  // ── Core arbitration ──────────────────────────────────
  async arbitrate({ taskId, requestingAgent, payload, format, targetRole, agents, webhookUrl }) {
    const receipt = {
      schema: "AxQxOS/TaskReceipt/v1",
      taskId,
      requestingAgent,
      targetRole,
      format,
      payload,
      webhookUrl: webhookUrl || null,
      status: "PENDING",
      createdAt: new Date().toISOString(),
      completedAt: null,
      result: null,
      assignedTo: null,
    };

    // Check if a suitable agent is live
    const liveAgents = [...agents.values()].filter(a => a.role === targetRole);
    receipt.status = liveAgents.length > 0 ? "ROUTED" : "QUEUED_FOR_SCAFFOLD";

    return receipt;
  }

  // ── Codestral scaffolding fallback ────────────────────
  async scaffoldViaCodestral(receipt) {
    const systemPrompt = this.buildSystemPrompt(receipt.targetRole);
    const userPrompt   = this.buildTaskPrompt(receipt);

    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user",   content: userPrompt   },
        ],
        temperature: 0.1,
        max_tokens: 4096,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`Codestral error ${response.status}: ${err}`);
    }

    const data  = await response.json();
    const raw   = data.choices?.[0]?.message?.content || "";

    return this.parseScaffoldOutput(raw, receipt.format);
  }

  // ── System prompt factory ──────────────────────────────
  buildSystemPrompt(role) {
    const rolePrompts = {
      AVATAR_CODEGEN: `You are the AxQxOS Avatar CodeGen Agent. Your task is to generate
production-grade Python code for embodied avatar runtime systems. You output
complete, runnable modules following the ADK v0 surface contract (capsule,
input artifact, transition, output artifact, receipt, block). All code must be
deterministic, immutable, and traceable. Return ONLY code blocks.`,

      RAG_RETRIEVER: `You are the AxQxOS RAG Retrieval Agent. Generate retrieval-augmented
generation pipelines using Google Gemini embeddings. Return structured JSON
with retrieval configs, index specs, and query templates.`,

      LORA_TRAINER: `You are the AxQxOS LoRA Training Agent. Generate LoRA fine-tuning
configurations and training loop code for Gemini-compatible models. Output
YAML configs and Python training loops. All weights are deterministic.`,

      WEBHOOK_DISPATCHER: `You are the AxQxOS Webhook Dispatcher. Generate webhook payload
schemas and dispatch logic in JSON, Markdown, and YAML formats.`,
    };

    return rolePrompts[role] || `You are an AxQxOS production agent for role: ${role}. 
Return complete, production-grade code artifacts.`;
  }

  // ── Task prompt factory ───────────────────────────────
  buildTaskPrompt(receipt) {
    const payloadStr = typeof receipt.payload === "string"
      ? receipt.payload
      : JSON.stringify(receipt.payload, null, 2);

    return `TASK_ID: ${receipt.taskId}
FORMAT:  ${receipt.format}
ROLE:    ${receipt.targetRole}

PAYLOAD:
${payloadStr}

Generate the complete implementation artifact for this task.
Output format: ${receipt.format.toUpperCase()}.
Prefix with: // AxQxOS/${receipt.taskId}`;
  }

  // ── Output parser ─────────────────────────────────────
  parseScaffoldOutput(raw, format) {
    if (format === "json") {
      const match = raw.match(/```json\n?([\s\S]*?)```/) || raw.match(/({[\s\S]*})/);
      try { return JSON.parse(match?.[1] || raw); } catch { return { raw }; }
    }
    if (format === "yaml") {
      const match = raw.match(/```yaml\n?([\s\S]*?)```/) || [null, raw];
      return { yaml: match[1] || raw };
    }
    // markdown or default
    return { markdown: raw };
  }
}
