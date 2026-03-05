// ============================================================
// AxQxOS WHAM Engine — Requirements MCP Server
// requirements-bots/mcp-requirements.js  |  v1.0.0
//
// Emulates PTC Integrity (RV&S) + IBM DOORS requirements
// management as a backend MCP for A2A witness testing.
// Runs as a GitHub Codespaces Extension Bot.
// ============================================================
import express from "express";
import { WebSocketServer } from "ws";
import { createServer } from "http";
import { randomUUID } from "crypto";
import yaml from "js-yaml";

const PORT = process.env.REQ_MCP_PORT || 3002;

const app  = express();
app.use(express.json());
const http = createServer(app);
const wss  = new WebSocketServer({ server: http });

// ── In-memory requirements store ─────────────────────────
const requirementsDB = {
  rvs:   new Map(),  // PTC RV&S items
  doors: new Map(),  // IBM DOORS objects
  traces: [],        // traceability links
  reviews: [],       // review sessions (A2A witness)
};

// ── Seed sample requirements ──────────────────────────────
function seedRequirements() {
  // PTC RV&S format
  requirementsDB.rvs.set("RVS-001", {
    id: "RVS-001", type: "Requirement", state: "Approved",
    summary: "WHAM Engine shall initialize the 2×2×2 lattice on startup",
    priority: "Must", assignee: "CELINE", capsule: "Cap.Zul",
    test_criteria: "init_lattice() returns 0 in WASM runtime",
  });
  requirementsDB.rvs.set("RVS-002", {
    id: "RVS-002", type: "Requirement", state: "InReview",
    summary: "Each Avatar Agent shall operate at its designated worldline node",
    priority: "Must", assignee: "DOT", capsule: "Glyph.Trace",
    test_criteria: "All 6 agents verified at correct [x,y,z] after init",
  });
  requirementsDB.rvs.set("RVS-003", {
    id: "RVS-003", type: "Requirement", state: "Draft",
    summary: "Token separation matmul shall complete in ≤50ms per 256-dim vector",
    priority: "Should", assignee: "GLOH", capsule: "LQQM",
    test_criteria: "Performance test: 1000 iterations, p99 ≤ 50ms",
  });

  // IBM DOORS format
  requirementsDB.doors.set("DOORS-SYS-001", {
    id: "DOORS-SYS-001", module: "WHAM-System-Requirements",
    level: 1, text: "The system shall provide deterministic, auditable agent dispatch",
    verification_method: "Test", status: "Baselined",
    linked_rvs: ["RVS-001", "RVS-002"],
  });
  requirementsDB.doors.set("DOORS-SW-001", {
    id: "DOORS-SW-001", module: "WHAM-Software-Requirements",
    level: 2, text: "All WASM module exports shall conform to the ADK v0 surface contract",
    verification_method: "Analysis + Test", status: "Draft",
    linked_rvs: ["RVS-001"],
    parent: "DOORS-SYS-001",
  });

  console.log(`[REQ-MCP] Seeded ${requirementsDB.rvs.size} RV&S items, ${requirementsDB.doors.size} DOORS objects`);
}

seedRequirements();

// ═══════════════════════════════════════════════════════════
// REST API — Requirements CRUD + Traceability
// ═══════════════════════════════════════════════════════════

// ── RV&S endpoints ────────────────────────────────────────
app.get("/rvs", (_, res) => {
  res.json({ items: [...requirementsDB.rvs.values()], count: requirementsDB.rvs.size });
});

app.get("/rvs/:id", (req, res) => {
  const item = requirementsDB.rvs.get(req.params.id);
  if (!item) return res.status(404).json({ error: "Not found" });
  res.json(item);
});

app.post("/rvs", (req, res) => {
  const id   = req.body.id || `RVS-${String(requirementsDB.rvs.size + 1).padStart(3, "0")}`;
  const item = { ...req.body, id, createdAt: new Date().toISOString() };
  requirementsDB.rvs.set(id, item);
  res.status(201).json(item);
});

app.patch("/rvs/:id", (req, res) => {
  const item = requirementsDB.rvs.get(req.params.id);
  if (!item) return res.status(404).json({ error: "Not found" });
  const updated = { ...item, ...req.body, updatedAt: new Date().toISOString() };
  requirementsDB.rvs.set(req.params.id, updated);
  res.json(updated);
});

// ── DOORS endpoints ───────────────────────────────────────
app.get("/doors", (_, res) => {
  res.json({ objects: [...requirementsDB.doors.values()], count: requirementsDB.doors.size });
});

app.get("/doors/:id", (req, res) => {
  const obj = requirementsDB.doors.get(req.params.id);
  if (!obj) return res.status(404).json({ error: "Not found" });
  res.json(obj);
});

// ── Traceability matrix ───────────────────────────────────
app.get("/rtm", (_, res) => {
  const rtm = [];
  for (const [doorsId, obj] of requirementsDB.doors) {
    for (const rvsId of (obj.linked_rvs || [])) {
      const rvsItem = requirementsDB.rvs.get(rvsId);
      rtm.push({
        doors_id: doorsId,
        rvs_id:   rvsId,
        coverage: rvsItem ? "LINKED" : "BROKEN",
        verification_method: obj.verification_method,
        test_criteria: rvsItem?.test_criteria,
      });
    }
  }
  res.json({ matrix: rtm, coverage: `${rtm.length} links` });
});

// ── RTM as YAML (for DOT agent RAG ingestion) ─────────────
app.get("/rtm.yaml", (_, res) => {
  const rtm = { traceability_matrix: [], generated_at: new Date().toISOString() };
  for (const [doorsId, obj] of requirementsDB.doors) {
    for (const rvsId of (obj.linked_rvs || [])) {
      rtm.traceability_matrix.push({ doors: doorsId, rvs: rvsId });
    }
  }
  res.set("Content-Type", "application/yaml");
  res.send(yaml.dump(rtm));
});

// ── Requirement-to-test mapping (for A2A witness) ─────────
app.get("/test-matrix", (_, res) => {
  const matrix = [...requirementsDB.rvs.values()].map(item => ({
    req_id:         item.id,
    summary:        item.summary,
    test_criteria:  item.test_criteria,
    assignee_agent: item.assignee,
    status:         item.state,
    test_result:    null,   // populated by DOT witness agent
  }));
  res.json({ test_matrix: matrix });
});

// ═══════════════════════════════════════════════════════════
// WEBSOCKET — A2A Witness Testing Sessions
// ═══════════════════════════════════════════════════════════

const witnessSessions = new Map();

wss.on("connection", (ws) => {
  const sessionId = randomUUID();
  witnessSessions.set(sessionId, { ws, log: [], startedAt: new Date().toISOString() });
  console.log(`[REQ-MCP] Witness session opened: ${sessionId}`);

  ws.send(JSON.stringify({
    type: "SESSION_INIT",
    sessionId,
    server: "AxQxOS Requirements MCP",
    schema: "AxQxOS/WitnessSession/v1",
    capabilities: ["rvs", "doors", "rtm", "test_matrix", "review"],
  }));

  ws.on("message", async (raw) => {
    let msg;
    try { msg = JSON.parse(raw.toString()); }
    catch { return ws.send(JSON.stringify({ type: "ERROR", code: "PARSE_FAIL" })); }

    const session = witnessSessions.get(sessionId);
    session.log.push({ ...msg, receivedAt: new Date().toISOString() });

    switch (msg.type) {
      case "FETCH_RTM":
        ws.send(JSON.stringify({
          type: "RTM",
          data: [...requirementsDB.doors.values()],
          rvs:  [...requirementsDB.rvs.values()],
        }));
        break;

      case "SUBMIT_TEST_RESULT":
        // DOT agent submits test results for requirements verification
        if (requirementsDB.rvs.has(msg.req_id)) {
          const item = requirementsDB.rvs.get(msg.req_id);
          item.test_result = msg.result;   // PASS | FAIL | SKIP
          item.witness     = sessionId;
          item.tested_at   = new Date().toISOString();
          requirementsDB.rvs.set(msg.req_id, item);
          ws.send(JSON.stringify({ type: "TEST_RECORDED", req_id: msg.req_id, result: msg.result }));

          // Broadcast to all witnesses
          broadcastWitness({ type: "TEST_UPDATE", req_id: msg.req_id, result: msg.result, witness: sessionId });
        }
        break;

      case "START_REVIEW":
        // PTC RV&S style review session
        const review = {
          id:          randomUUID(),
          session:     sessionId,
          req_ids:     msg.req_ids || [],
          agent:       msg.agent || "DOT",
          status:      "OPEN",
          startedAt:   new Date().toISOString(),
        };
        requirementsDB.reviews.push(review);
        ws.send(JSON.stringify({ type: "REVIEW_STARTED", review }));
        break;

      case "CLOSE_REVIEW":
        const rev = requirementsDB.reviews.find(r => r.id === msg.review_id);
        if (rev) {
          rev.status     = "CLOSED";
          rev.closedAt   = new Date().toISOString();
          rev.resolution = msg.resolution;
          ws.send(JSON.stringify({ type: "REVIEW_CLOSED", review: rev }));
        }
        break;
    }
  });

  ws.on("close", () => {
    const session = witnessSessions.get(sessionId);
    console.log(`[REQ-MCP] Witness session closed: ${sessionId} (${session?.log.length} events)`);
    witnessSessions.delete(sessionId);
  });
});

function broadcastWitness(msg) {
  const raw = JSON.stringify(msg);
  for (const { ws } of witnessSessions.values()) {
    if (ws.readyState === 1) ws.send(raw);
  }
}

// ── Health ────────────────────────────────────────────────
app.get("/health", (_, res) => res.json({
  status:   "OK",
  rvs:      requirementsDB.rvs.size,
  doors:    requirementsDB.doors.size,
  sessions: witnessSessions.size,
  schema:   "AxQxOS/RequirementsMCP/v1",
}));

http.listen(PORT, () => {
  console.log(`[REQ-MCP] Requirements MCP live on :${PORT}`);
  console.log("[REQ-MCP] PTC RV&S + IBM DOORS emulation active");
  console.log("[REQ-MCP] A2A Witness WebSocket ready");
});
