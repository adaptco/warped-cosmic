// firebase/functions/index.js
// Firebase Cloud Functions — Agent Forge backend
// Hosts webhook receivers, Zapier job triggers, and Vertex AI UX generation endpoints

const functions = require("firebase-functions");
const admin = require("firebase-admin");
const { Anthropic } = require("@anthropic-ai/sdk");

admin.initializeApp();
const db = admin.firestore();

// ─────────────────────────────────────────────────────────────────────────────
// WEBHOOK RECEIVER — receives A2A envelopes from Echo relay
// ─────────────────────────────────────────────────────────────────────────────
exports.receiveWebhook = functions.https.onRequest(async (req, res) => {
  if (req.method !== "POST") return res.status(405).send("Method Not Allowed");

  const envelope = req.body;
  if (!envelope.task_id || !envelope.from_agent) {
    return res.status(400).json({ error: "Invalid A2A envelope" });
  }

  // Log to Firestore
  await db.collection("webhook_events").add({
    ...envelope,
    received_at: admin.firestore.FieldValue.serverTimestamp(),
  });

  // Route to appropriate handler
  switch (envelope.task_id) {
    case "T-004":
      await triggerSlackDiscord(envelope.payload);
      break;
    case "T-005":
      await createPMTasks(envelope.payload);
      break;
    case "T-011":
      await finalizeDeployment(envelope.payload);
      break;
  }

  res.json({ accepted: true, task_id: envelope.task_id });
});

// ─────────────────────────────────────────────────────────────────────────────
// SCAFFOLD API — Claude-powered scaffold generation
// ─────────────────────────────────────────────────────────────────────────────
exports.generateScaffold = functions.https.onRequest(async (req, res) => {
  // Enable CORS for Claude artifact calls
  res.set("Access-Control-Allow-Origin", "*");
  res.set("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).send("");

  const { description, stack } = req.body;
  if (!description) return res.status(400).json({ error: "description required" });

  const client = new Anthropic({ apiKey: functions.config().anthropic.api_key });
  const response = await client.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1000,
    system: "Generate a production project scaffold. Be specific and technical.",
    messages: [{ role: "user", content: `Stack: ${JSON.stringify(stack)}\n\nProject: ${description}` }],
  });

  const scaffold = response.content[0].text;
  await db.collection("scaffolds").add({ description, stack, scaffold, created_at: admin.firestore.FieldValue.serverTimestamp() });
  res.json({ scaffold });
});

// ─────────────────────────────────────────────────────────────────────────────
// ZAPIER TRIGGER — fires Zapier zap to orchestrate cloud jobs
// ─────────────────────────────────────────────────────────────────────────────
exports.triggerZapierJob = functions.https.onRequest(async (req, res) => {
  const ZAPIER_HOOK = functions.config().zapier?.webhook_url;
  if (!ZAPIER_HOOK) return res.status(503).json({ error: "Zapier webhook not configured" });

  const payload = { ...req.body, source: "agent-forge", timestamp: new Date().toISOString() };
  const fetch = require("node-fetch");
  const r = await fetch(ZAPIER_HOOK, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  res.json({ zapier_status: r.status, payload });
});

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────
async function triggerSlackDiscord(payload) {
  const fetch = require("node-fetch");
  const slackUrl = functions.config().slack?.webhook_url;
  const discordUrl = functions.config().discord?.webhook_url;
  if (slackUrl) await fetch(slackUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: `🤖 Agent Forge: ${payload.message || "Task update"}` }) });
  if (discordUrl) await fetch(discordUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: `**Agent Forge** ${payload.message || "Task update"}` }) });
}

async function createPMTasks(payload) {
  await db.collection("pm_tasks").add({ ...payload, created_at: admin.firestore.FieldValue.serverTimestamp() });
}

async function finalizeDeployment(payload) {
  await db.collection("deployments").add({ ...payload, deployed_at: admin.firestore.FieldValue.serverTimestamp() });
}
