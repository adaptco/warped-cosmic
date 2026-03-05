// ============================================================
// AxQxOS WHAM Engine — JavaScript Host Shell
// wham-engine/wham-shell.js  |  v1.0.0
//
// Docks WASM containers (World Models), threads embedding
// vectors as isometric worldlines, dispatches avatar agents.
// ============================================================

import { readFileSync } from "fs";
import { createHash } from "crypto";

const WHAM_VERSION = "v1.0.0";
const EMBED_DIM    = 1536;  // Full Gemini dim (host-side)
const WASM_DIM     = 256;   // Truncated WASM-safe dim

// ── Agent manifest ────────────────────────────────────────
const AGENTS = [
  { id: 0, name: "CELINE", capsule: "Cap.Zul",    worldline: [0,0,0], particle: "Gauge Boson" },
  { id: 1, name: "SPRYTE", capsule: "Qube™",       worldline: [1,0,0], particle: "Photon"      },
  { id: 2, name: "ECHO",   capsule: "Echo.Mesh",   worldline: [0,1,0], particle: "Neutrino"    },
  { id: 3, name: "GLOH",   capsule: "LQQM",        worldline: [1,1,0], particle: "Gluon"       },
  { id: 4, name: "LUMA",   capsule: "Sol.F1",      worldline: [0,0,1], particle: "Graviton"    },
  { id: 5, name: "DOT",    capsule: "Glyph.Trace", worldline: [1,1,1], particle: "Electron"    },
];

// ── World Model Container ─────────────────────────────────
class WorldModelContainer {
  constructor(id, agentId, embedding) {
    this.id        = id;
    this.agentId   = agentId;
    this.embedding = embedding;        // Float32Array[1536]
    this.state     = "DOCKED";
    this.taskQueue = [];
    this.receipts  = [];
    this.yieldAcc  = 0.0;
  }

  enqueue(task) {
    this.taskQueue.push({ ...task, enqueuedAt: Date.now() });
  }

  emitReceipt(result, yieldSignal) {
    const receipt = {
      schema:      "AxQxOS/WorldModelReceipt/v1",
      containerId: this.id,
      agentId:     this.agentId,
      yieldSignal,
      result,
      hash:        createHash("sha256")
                     .update(JSON.stringify(result))
                     .digest("hex"),
      timestamp:   new Date().toISOString(),
    };
    this.receipts.push(receipt);
    this.yieldAcc += yieldSignal;
    return receipt;
  }
}

// ── WHAM Engine ───────────────────────────────────────────
export class WHAMEngine {
  constructor(wasmPath) {
    this.wasmPath   = wasmPath;
    this.wasm       = null;
    this.memory     = null;
    this.containers = new Map();   // containerId → WorldModelContainer
    this.worldlines = new Map();   // "agentA-agentB" → similarity
    this.ledger     = [];
    this.initialized = false;
  }

  // ── Boot ─────────────────────────────────────────────
  async init() {
    const bytes = readFileSync(this.wasmPath);
    const { instance } = await WebAssembly.instantiate(bytes, {
      env: {
        // Host callbacks for agent MoE routing
        __wham_log: (ptr, len) => {
          const bytes = new Uint8Array(this.memory.buffer, ptr, len);
          console.log("[WASM]", new TextDecoder().decode(bytes));
        },
      },
    });

    this.exports = instance.exports;
    this.memory  = instance.exports.memory;
    this.exports.init_lattice();
    this.initialized = true;

    console.log(`[WHAM] Engine ${WHAM_VERSION} initialized. Lattice: 2×2×2`);
    this._logLattice();
  }

  // ── Dock a World Model Container ─────────────────────
  dock(agentName, embedding) {
    const agent = AGENTS.find(a => a.name === agentName);
    if (!agent) throw new Error(`Unknown agent: ${agentName}`);

    const container = new WorldModelContainer(
      `wm-${agentName}-${Date.now()}`,
      agent.id,
      embedding,
    );

    this.containers.set(container.id, container);

    // Write truncated embedding to WASM memory (page 1)
    const mem = new Float32Array(this.memory.buffer);
    const offset = 65536 / 4 + agent.id * WASM_DIM;  // Page 1
    const truncated = this._truncateEmbed(embedding, WASM_DIM);
    mem.set(truncated, offset);

    console.log(`[WHAM] Docked: ${agentName} → ${container.id} at [${agent.worldline}]`);
    return container;
  }

  // ── Thread worldlines (compute pairwise similarity) ──
  threadWorldlines(embeddings) {
    // embeddings: Map<agentName, Float32Array>
    const names = [...embeddings.keys()];

    for (let i = 0; i < names.length; i++) {
      for (let j = i + 1; j < names.length; j++) {
        const a = names[i], b = names[j];
        const sim = this._cosine(embeddings.get(a), embeddings.get(b));
        const key = `${a}-${b}`;
        this.worldlines.set(key, sim);

        if (sim >= 0.60) {
          console.log(`[WHAM] Worldline active: ${a} ↔ ${b} (ρ=${sim.toFixed(4)})`);
        }
      }
    }

    return Object.fromEntries(this.worldlines);
  }

  // ── Dispatch task to agent at lattice node ────────────
  dispatch(agentName, task) {
    const agent = AGENTS.find(a => a.name === agentName);
    if (!agent) throw new Error(`Unknown agent: ${agentName}`);

    const [x, y, z] = agent.worldline;

    // Write task to WASM memory (page 2) - simplified as task ID
    const mem32 = new Int32Array(this.memory.buffer);
    const taskOffset = (65536 * 2) / 4;
    mem32[taskOffset] = this._taskHash(task);

    // Dispatch via WASM function table
    const yieldSignal = this.exports.dispatch_agent(x, y, z, 65536 * 2);

    console.log(`[WHAM] Dispatched to ${agentName} [${x},${y},${z}] → yield: ${yieldSignal.toFixed(6)}`);

    // Find container for this agent and emit receipt
    const container = [...this.containers.values()]
      .find(c => c.agentId === agent.id);

    if (container) {
      return container.emitReceipt({ task, agent: agentName }, yieldSignal);
    }

    return { agentName, yieldSignal, task, timestamp: new Date().toISOString() };
  }

  // ── Particle-antiparticle annihilation (VH2 ⊗ VH100) ─
  annihilate(vh2Embedding, vh100Embedding) {
    const electronEnergy = this._norm(vh2Embedding);
    const positronEnergy = this._norm(vh100Embedding);

    const gammaYield = this.exports.pair_annihilate(
      electronEnergy,
      positronEnergy,
    );

    const event = {
      schema:         "AxQxOS/AnnihilationEvent/v1",
      electron:       { model: "VH2", energy: electronEnergy  },
      positron:       { model: "VH100", energy: positronEnergy },
      gamma_yield:    gammaYield,
      phase_change:   "repo_structure → code_execution",
      token_destroyed: "VH100",
      token_survived:  "VH2",
      timestamp:      new Date().toISOString(),
      canonical:      "Canonical truth, attested and replayable.",
    };

    this.ledger.push(event);
    console.log(`[WHAM] ⚡ Annihilation: VH2 × VH100 → γ=${gammaYield.toFixed(6)}`);
    return event;
  }

  // ── Token separation via matmul abstraction layer ─────
  separateTokens(inputVec, weightMatrix) {
    // Write to WASM memory
    const mem = new Float32Array(this.memory.buffer);
    const matOffset  = (65536 * 3) / 4;
    const vecOffset  = matOffset + WASM_DIM * WASM_DIM;
    const outOffset  = vecOffset + WASM_DIM;

    // Write truncated matrix and vector
    const mat = this._truncateEmbed(weightMatrix, WASM_DIM * WASM_DIM);
    const vec = this._truncateEmbed(inputVec, WASM_DIM);
    mem.set(mat, matOffset);
    mem.set(vec, vecOffset);

    this.exports.matmul_token_layer(
      matOffset * 4,
      vecOffset * 4,
      outOffset * 4,
      WASM_DIM,
    );

    // Read output
    const out = new Float32Array(this.memory.buffer, outOffset * 4, WASM_DIM);
    return Float32Array.from(out);
  }

  // ── Quantum SDE yield curve ───────────────────────────
  yieldCurve(maxQuanta = 10, omega = 1.618) {
    const curve = [];
    for (let n = 0; n <= maxQuanta; n++) {
      const y = this.exports.sde_yield(n, omega);
      curve.push({ n, omega, yield: y });
    }
    return curve;
  }

  // ── Internal helpers ──────────────────────────────────
  _cosine(a, b) {
    let dot = 0, na = 0, nb = 0;
    const len = Math.min(a.length, b.length);
    for (let i = 0; i < len; i++) {
      dot += a[i] * b[i];
      na  += a[i] * a[i];
      nb  += b[i] * b[i];
    }
    return dot / (Math.sqrt(na) * Math.sqrt(nb) + 1e-10);
  }

  _norm(v) {
    return Math.sqrt(v.reduce((s, x) => s + x * x, 0));
  }

  _truncateEmbed(v, dim) {
    if (v.length >= dim) return v.slice(0, dim);
    const out = new Float32Array(dim);
    out.set(v);
    return out;
  }

  _taskHash(task) {
    return parseInt(
      createHash("sha256").update(JSON.stringify(task)).digest("hex").slice(0, 8),
      16,
    );
  }

  _logLattice() {
    console.log("[WHAM] Lattice nodes:");
    for (const a of AGENTS) {
      console.log(`  ${a.name.padEnd(8)} [${a.worldline}]  ${a.particle}  capsule:${a.capsule}`);
    }
  }
}

// ── CLI smoke test ────────────────────────────────────────
if (process.argv[1].endsWith("wham-shell.js")) {
  const engine = new WHAMEngine("./wham.wasm");
  await engine.init();

  // Smoke: yield curve
  const curve = engine.yieldCurve(5, 1.618);
  console.log("[WHAM] Yield curve (n=0..5, ω=φ):", curve);

  // Smoke: annihilation
  const vh2  = new Float32Array(256).fill(0.5);
  const vh100 = new Float32Array(256).fill(0.3);
  const event = engine.annihilate(vh2, vh100);
  console.log("[WHAM] Annihilation event:", event);
}
