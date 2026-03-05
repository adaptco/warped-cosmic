// ============================================================
// AxQxOS Avatar Engine — MCP A2A Arbitration Server
// mcp-server/index.js  |  v1.0.0
// Agent-to-Agent comms via Codestral API
// ============================================================
import express from "express";
import { createServer } from "http";
import { WebSocketServer } from "ws";
import { randomUUID } from "crypto";
import yaml from "js-yaml";
import { marked } from "marked";
import { ArbitrationLayer } from "./a2a-arbiter.js";
import { WebhookRouter } from "./webhook-router.js";

const PORT = process.env.MCP_PORT || 3001;
const CODESTRAL_API_KEY = process.env.CODESTRAL_API_KEY;
const CODESTRAL_BASE = "https://codestral.mistral.ai/v1";
const AVATAR_ENGINE_VERSION = "v1.0.0";

// ── App bootstrap ─────────────────────────────────────────
const app = express();
app.use(express.json());
app.use(express.text({ type: ["text/markdown", "text/yaml"] }));

const httpServer = createServer(app);
const wss = new WebSocketServer({ server: httpServer });
const arbiter = new ArbitrationLayer(CODESTRAL_API_KEY, CODESTRAL_BASE);
const webhookRouter = new WebhookRouter();

// ── Active agent registry ─────────────────────────────────
const agentRegistry = new Map();   // agentId → { ws, role, capsule, state }
const taskLedger    = new Map();   // taskId  → TaskReceipt

// ── WebSocket: Agent session ──────────────────────────────
wss.on("connection", (ws, req) => {
  const agentId = randomUUID();
  const sessionStart = new Date().toISOString();

  agentRegistry.set(agentId, {
    ws,
    role: null,
    capsule: null,
    state: "CONNECTED",
    sessionStart,
  });

  console.log(`[MCP] Agent connected: ${agentId}`);

  ws.send(JSON.stringify({
    type: "SESSION_INIT",
    agentId,
    serverVersion: AVATAR_ENGINE_VERSION,
    timestamp: sessionStart,
  }));

  ws.on("message", async (raw) => {
    let msg;
    try { msg = JSON.parse(raw.toString()); }
    catch { return ws.send(JSON.stringify({ type: "ERROR", code: "PARSE_FAIL" })); }

    await handleAgentMessage(agentId, msg, ws);
  });

  ws.on("close", () => {
    console.log(`[MCP] Agent disconnected: ${agentId}`);
    agentRegistry.delete(agentId);
  });
});

// ── Agent message dispatcher ──────────────────────────────
async function handleAgentMessage(agentId, msg, ws) {
  const agent = agentRegistry.get(agentId);
  if (!agent) return;

  switch (msg.type) {

    case "REGISTER": {
      agent.role    = msg.role;     // e.g. "AVATAR_CODEGEN", "RAG_RETRIEVER", "LORA_TRAINER"
      agent.capsule = msg.capsule;  // AxQxOS capsule binding
      agent.state   = "REGISTERED";
      agentRegistry.set(agentId, agent);
      ws.send(JSON.stringify({ type: "REGISTERED", agentId, role: agent.role }));
      broadcastToAll({ type: "AGENT_JOINED", agentId, role: agent.role });
      break;
    }

    case "TASK_REQUEST": {
      const taskId = `task-${randomUUID()}`;
      const receipt = await arbiter.arbitrate({
        taskId,
        requestingAgent: agentId,
        payload: msg.payload,
        format: msg.format || "json",  // json | markdown | yaml
        targetRole: msg.targetRole,
        agents: agentRegistry,
      });

      taskLedger.set(taskId, receipt);
      ws.send(JSON.stringify({ type: "TASK_ACCEPTED", taskId, receipt }));

      // Route to target agent(s)
      await routeTask(taskId, receipt);
      break;
    }

    case "TASK_RESULT": {
      const entry = taskLedger.get(msg.taskId);
      if (!entry) { ws.send(JSON.stringify({ type: "ERROR", code: "TASK_NOT_FOUND" })); break; }

      entry.result  = msg.result;
      entry.status  = "COMPLETE";
      entry.completedAt = new Date().toISOString();
      taskLedger.set(msg.taskId, entry);

      // Fire webhook if registered
      if (entry.webhookUrl) {
        await webhookRouter.dispatch(entry.webhookUrl, entry, entry.format);
      }

      // Notify requesting agent
      const requester = agentRegistry.get(entry.requestingAgent);
      if (requester?.ws?.readyState === 1) {
        requester.ws.send(JSON.stringify({ type: "TASK_COMPLETE", taskId: msg.taskId, result: msg.result }));
      }
      break;
    }

    default:
      ws.send(JSON.stringify({ type: "ERROR", code: "UNKNOWN_TYPE", received: msg.type }));
  }
}

// ── Route task to appropriate agent ───────────────────────
async function routeTask(taskId, receipt) {
  const targetAgents = [...agentRegistry.entries()]
    .filter(([_, a]) => a.role === receipt.targetRole && a.state === "REGISTERED");

  if (!targetAgents.length) {
    // No live agent — scaffold via Codestral
    const scaffolded = await arbiter.scaffoldViaCodestral(receipt);
    receipt.result   = scaffolded;
    receipt.status   = "SCAFFOLDED";
    taskLedger.set(taskId, receipt);
    return;
  }

  // Distribute to first available (round-robin can be layered here)
  const [targetId, targetAgent] = targetAgents[0];
  targetAgent.ws.send(JSON.stringify({
    type: "TASK_ASSIGNED",
    taskId,
    payload: receipt.payload,
    format: receipt.format,
  }));
  receipt.assignedTo = targetId;
  taskLedger.set(taskId, receipt);
}

// ── Broadcast helper ──────────────────────────────────────
function broadcastToAll(msg) {
  const raw = JSON.stringify(msg);
  for (const { ws } of agentRegistry.values()) {
    if (ws.readyState === 1) ws.send(raw);
  }
}

// ── REST: Task submission via webhook ─────────────────────
app.post("/webhook/task", async (req, res) => {
  const contentType = req.headers["content-type"] || "application/json";
  let payload;

  if (contentType.includes("yaml")) {
    payload = yaml.load(req.body);
  } else if (contentType.includes("markdown")) {
    payload = { markdown: req.body, html: marked(req.body) };
  } else {
    payload = req.body;
  }

  const taskId = `webhook-task-${randomUUID()}`;
  const receipt = await arbiter.arbitrate({
    taskId,
    requestingAgent: "WEBHOOK",
    payload,
    format: contentType.includes("yaml") ? "yaml" : contentType.includes("markdown") ? "markdown" : "json",
    targetRole: payload.targetRole || "AVATAR_CODEGEN",
    agents: agentRegistry,
    webhookUrl: payload.callbackUrl,
  });

  taskLedger.set(taskId, receipt);
  await routeTask(taskId, receipt);

  res.json({ taskId, status: receipt.status, receipt });
});

// ── REST: Task status ─────────────────────────────────────
app.get("/task/:taskId", (req, res) => {
  const entry = taskLedger.get(req.params.taskId);
  if (!entry) return res.status(404).json({ error: "Not found" });
  res.json(entry);
});

// ── REST: Agent registry ──────────────────────────────────
app.get("/agents", (_, res) => {
  const agents = [...agentRegistry.entries()].map(([id, a]) => ({
    id, role: a.role, capsule: a.capsule, state: a.state, sessionStart: a.sessionStart,
  }));
  res.json({ agents, count: agents.length });
});

// ── REST: Health ──────────────────────────────────────────
app.get("/health", (_, res) => res.json({
  status: "OK",
  version: AVATAR_ENGINE_VERSION,
  agents: agentRegistry.size,
  tasks: taskLedger.size,
  timestamp: new Date().toISOString(),
}));

// ── Start ─────────────────────────────────────────────────
httpServer.listen(PORT, () => {
  console.log(`[MCP] AxQxOS A2A Server live on :${PORT}`);
  console.log(`[MCP] Codestral arbitration: ${CODESTRAL_BASE}`);
  console.log(`[MCP] Canonical truth, attested and replayable.`);
});

export { agentRegistry, taskLedger };
