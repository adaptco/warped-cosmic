import { useState } from "react";

const AGENTS = [
  {
    id: "CELINE", particle: "Gauge Boson", capsule: "Cap.Zul",
    worldline: [0,0,0], token: "AXIS·SOULOS",
    color: "#7B6EF6", glow: "#7B6EF680",
    role: "Sovereign Orchestrator",
    moe: ["GovernanceExpert 40%", "OrchestrationExpert 35%", "AuditExpert 25%"],
    sod: ["SOD-CL-001 Council Quorum", "SOD-CL-002 Override Adjudication", "SOD-CL-003 SSOT Audit"],
    tools: ["council-quorum.yml", "override-adjudicate.yml", "ssot-audit.yml", "mcp_task_dispatch"],
    skills: ["Multi-agent task routing", "Maker-Checker governance", "RFC8785 canonicalization", "Merkle anchoring"],
    backend: "Gemini 1.5 Pro",
  },
  {
    id: "SPRYTE", particle: "Photon", capsule: "Qube™",
    worldline: [1,0,0], token: "LUMEN·BLOOM",
    color: "#B565F7", glow: "#B565F780",
    role: "Frontend & UI Codegen",
    moe: ["ReactExpert 35%", "WASMExpert 30%", "ThreeJSExpert 20%", "DesignExpert 15%"],
    sod: ["SOD-SP-001 Agent Card Component", "SOD-SP-002 WHAM Isometric Renderer", "SOD-SP-003 A2A Witness Dashboard"],
    tools: ["ui-build.yml", "wasm-compile.yml", "codestral_component_gen"],
    skills: ["React/TypeScript codegen", "WASM shell authoring", "Isometric world renderer", "Vanilla CSS systems"],
    backend: "Codestral",
  },
  {
    id: "ECHO", particle: "Neutrino", capsule: "Echo.Mesh",
    worldline: [0,1,0], token: "TRACE·PLUG",
    color: "#3DD9A4", glow: "#3DD9A480",
    role: "RAG Retrieval & Harmonization",
    moe: ["EmbeddingExpert 40%", "RetrievalExpert 35%", "HarmonizationExpert 25%"],
    sod: ["SOD-EC-001 Requirements RAG Index", "SOD-EC-002 Capsule Replay Verify", "SOD-EC-003 Federated Sync"],
    tools: ["rag-index.yml", "gemini_embed (dim=1536)", "requirements_ingest MCP"],
    skills: ["Gemini embeddings 1536-dim", "Vector index + semantic retrieval", "Echo.Mesh federation", "RV&S / DOORS → RAG"],
    backend: "Gemini text-embedding-004",
  },
  {
    id: "GLOH", particle: "Gluon", capsule: "LQQM",
    worldline: [1,1,0], token: "GLOH·PEACHES·BLOOM",
    color: "#F5C542", glow: "#F5C54280",
    role: "Token Economics & SDE Signal",
    moe: ["YieldExpert 40%", "TokenomicsExpert 35%", "MatrixExpert 25%"],
    sod: ["SOD-GL-001 Quantum Yield Curve", "SOD-GL-002 Token Flow Simulation", "SOD-GL-003 OPEX Sovereign Map"],
    tools: ["yield-curve.yml", "token-sync.yml", "gemini_yield_model"],
    skills: ["Quantum SDE yield calc", "Dynamic TAPD yield", "Cross-stack token sync", "Matmul abstraction layer"],
    backend: "Gemini 1.5 Flash",
  },
  {
    id: "LUMA", particle: "Graviton", capsule: "Sol.F1",
    worldline: [0,0,1], token: "LUMEN·AXIS",
    color: "#FF5E5E", glow: "#FF5E5E80",
    role: "Render & Cinematic Codegen",
    moe: ["VehicleRenderExpert 40%", "WebGLExpert 35%", "AvatarRenderExpert 25%"],
    sod: ["SOD-LM-001 VH2 Render Context", "SOD-LM-002 Sol.F1 Mecha Wireframe", "SOD-LM-003 WHAM Isometric Scene"],
    tools: ["render-pipeline.yml", "wasm_renderer", "vertex_vision"],
    skills: ["C5_SYMMETRY enforcement", "VH2 electron model renders", "Three.js / WebGL scenes", "Sol.F1 wireframe (neon-cyan)"],
    backend: "Gemini 1.5 Pro Vision",
    prime: true,
  },
  {
    id: "DOT", particle: "Electron", capsule: "Glyph.Trace",
    worldline: [1,1,1], token: "TRACE·PLUG",
    color: "#5BB8FF", glow: "#5BB8FF80",
    role: "Witness Testing & QA",
    moe: ["WitnessExpert 35%", "RequirementsExpert 35%", "AutomationExpert 30%"],
    sod: ["SOD-DT-001 A2A Witness Session", "SOD-DT-002 PR Autocode & Merge", "SOD-DT-003 RTM Generation"],
    tools: ["witness-test.yml", "daily-mlops.yml", "requirements_mcp", "codestral_autocode"],
    skills: ["A2A witness testing", "PR autocode + merge", "PTC RV&S emulation", "IBM DOORS traceability"],
    backend: "Codestral",
  },
];

const WORLDLINES = [
  ["CELINE","SPRYTE"], ["CELINE","ECHO"], ["CELINE","GLOH"], ["CELINE","DOT"],
  ["SPRYTE","LUMA"], ["ECHO","GLOH"], ["ECHO","DOT"], ["GLOH","DOT"], ["LUMA","DOT"],
];

const TAB_LABELS = ["SKILL.md", "MoE", "SOD", "TOOLS.md"];

function LatticeViz({ agents, activeAgent, onSelect }) {
  const positions = {
    CELINE: [50, 28], SPRYTE: [78, 28],
    ECHO:   [36, 52], GLOH:   [64, 52],
    LUMA:   [22, 76], DOT:    [78, 76],
  };

  return (
    <svg viewBox="0 0 100 100" style={{ width: "100%", height: "100%", overflow: "visible" }}>
      <defs>
        {agents.map(a => (
          <filter key={a.id} id={`glow-${a.id}`}>
            <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
            <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        ))}
      </defs>

      {WORLDLINES.map(([a, b]) => {
        const [x1, y1] = positions[a];
        const [x2, y2] = positions[b];
        const isActive = activeAgent && (activeAgent === a || activeAgent === b);
        return (
          <line key={`${a}-${b}`}
            x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={isActive ? "#ffffff40" : "#ffffff18"}
            strokeWidth={isActive ? "0.6" : "0.3"}
            strokeDasharray={isActive ? "none" : "1,1"}
          />
        );
      })}

      {agents.map(a => {
        const [cx, cy] = positions[a.id];
        const active = activeAgent === a.id;
        return (
          <g key={a.id} onClick={() => onSelect(a.id)}
             style={{ cursor: "pointer" }}>
            <circle cx={cx} cy={cy} r={active ? 6 : 4.5}
              fill={a.color + "22"} stroke={a.color}
              strokeWidth={active ? "1.2" : "0.7"}
              filter={active ? `url(#glow-${a.id})` : "none"}
            />
            <circle cx={cx} cy={cy} r={active ? 2.2 : 1.8}
              fill={a.color} opacity={active ? 1 : 0.75}
              filter={`url(#glow-${a.id})`}
            />
            <text x={cx} y={cy - 7.5} textAnchor="middle"
              fill={active ? "#fff" : a.color}
              fontSize="3.8" fontFamily="'Space Mono', monospace"
              fontWeight={active ? "700" : "400"}
            >{a.id}</text>
            <text x={cx} y={cy + 9} textAnchor="middle"
              fill="#ffffff50" fontSize="2.4" fontFamily="monospace"
            >[{a.worldline.join(",")}]</text>
          </g>
        );
      })}
    </svg>
  );
}

function AgentCard({ agent, onClose }) {
  const [tab, setTab] = useState(0);

  const tabContent = [
    // SKILL.md
    <div key="skill" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ color: "#ffffff90", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>
        Capabilities
      </div>
      {agent.skills.map((s, i) => (
        <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
          <span style={{ color: agent.color, fontSize: 10, marginTop: 1 }}>◆</span>
          <span style={{ color: "#d4d4d4", fontSize: 12, lineHeight: 1.5 }}>{s}</span>
        </div>
      ))}
      {agent.prime && (
        <div style={{ marginTop: 8, padding: "8px 10px", background: "#FF5E5E18",
          border: "1px solid #FF5E5E60", borderRadius: 4, fontSize: 11, color: "#FF9999" }}>
          ⚡ PRIME_DIRECTIVE: C5_SYMMETRY · 5-spoke Advan GT Beyond · RSM
        </div>
      )}
    </div>,

    // MoE
    <div key="moe" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ color: "#ffffff90", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>
        Mixture of Experts
      </div>
      {agent.moe.map((e, i) => {
        const [name, pct] = e.split(" ");
        const w = parseInt(pct);
        return (
          <div key={i}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
              <span style={{ color: "#c4c4c4", fontSize: 12 }}>{name}</span>
              <span style={{ color: agent.color, fontSize: 11, fontFamily: "monospace" }}>{pct}</span>
            </div>
            <div style={{ height: 3, background: "#ffffff15", borderRadius: 2 }}>
              <div style={{ width: `${w}%`, height: "100%", background: agent.color,
                borderRadius: 2, opacity: 0.8 }} />
            </div>
          </div>
        );
      })}
      <div style={{ marginTop: 8, color: "#ffffff50", fontSize: 11 }}>
        Backend: <span style={{ color: agent.color }}>{agent.backend}</span>
      </div>
    </div>,

    // SOD
    <div key="sod" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ color: "#ffffff90", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>
        Software on Demand
      </div>
      {agent.sod.map((s, i) => {
        const [id, ...rest] = s.split(" ");
        return (
          <div key={i} style={{ padding: "7px 10px", background: "#ffffff08",
            borderRadius: 4, border: `1px solid ${agent.color}30` }}>
            <div style={{ color: agent.color, fontSize: 10, fontFamily: "monospace", marginBottom: 2 }}>{id}</div>
            <div style={{ color: "#d4d4d4", fontSize: 12 }}>{rest.join(" ")}</div>
          </div>
        );
      })}
    </div>,

    // TOOLS.md
    <div key="tools" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ color: "#ffffff90", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>
        GitHub Actions & Tools
      </div>
      {agent.tools.map((t, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8,
          padding: "6px 10px", background: "#0D1117", borderRadius: 4,
          border: "1px solid #30363D" }}>
          <span style={{ fontSize: 10 }}>{t.endsWith(".yml") ? "⚙️" : "🔌"}</span>
          <code style={{ color: "#58A6FF", fontSize: 11 }}>{t}</code>
        </div>
      ))}
    </div>,
  ];

  return (
    <div style={{
      position: "fixed", inset: 0, background: "#00000080",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 100, backdropFilter: "blur(4px)",
    }} onClick={onClose}>
      <div style={{
        width: 480, maxHeight: "80vh", background: "#0E0E1A",
        border: `1px solid ${agent.color}50`, borderRadius: 12,
        boxShadow: `0 0 40px ${agent.glow}, 0 20px 60px #000000A0`,
        overflow: "hidden", display: "flex", flexDirection: "column",
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ padding: "16px 20px", background: `${agent.color}12`,
          borderBottom: `1px solid ${agent.color}30`,
          display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%",
                background: agent.color, boxShadow: `0 0 8px ${agent.color}` }} />
              <span style={{ color: agent.color, fontSize: 18, fontFamily: "'Space Mono', monospace",
                fontWeight: 700, letterSpacing: 2 }}>{agent.id}</span>
              <span style={{ color: "#ffffff50", fontSize: 11, fontFamily: "monospace" }}>
                [{agent.worldline.join(",")}]
              </span>
            </div>
            <div style={{ color: "#c4c4c4", fontSize: 12, marginBottom: 2 }}>{agent.role}</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <span style={{ color: "#ffffff50", fontSize: 10, fontFamily: "monospace" }}>
                capsule: <span style={{ color: agent.color }}>{agent.capsule}</span>
              </span>
              <span style={{ color: "#ffffff50", fontSize: 10, fontFamily: "monospace" }}>
                particle: <span style={{ color: "#ffffff80" }}>{agent.particle}</span>
              </span>
              <span style={{ color: "#ffffff50", fontSize: 10, fontFamily: "monospace" }}>
                token: <span style={{ color: agent.color }}>{agent.token}</span>
              </span>
            </div>
          </div>
          <button onClick={onClose}
            style={{ background: "none", border: "none", color: "#ffffff50",
              fontSize: 18, cursor: "pointer", lineHeight: 1 }}>✕</button>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid #ffffff15" }}>
          {TAB_LABELS.map((label, i) => (
            <button key={i} onClick={() => setTab(i)}
              style={{
                flex: 1, padding: "10px 0", background: "none",
                border: "none", cursor: "pointer", fontSize: 11,
                fontFamily: "'Space Mono', monospace", letterSpacing: 0.5,
                color: tab === i ? agent.color : "#ffffff40",
                borderBottom: tab === i ? `2px solid ${agent.color}` : "2px solid transparent",
                transition: "all 0.15s",
              }}>{label}</button>
          ))}
        </div>

        {/* Content */}
        <div style={{ padding: "16px 20px", overflowY: "auto", flex: 1 }}>
          {tabContent[tab]}
        </div>
      </div>
    </div>
  );
}

export default function WHAMAgentsDashboard() {
  const [activeAgent, setActiveAgent] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const agent = selectedAgent ? AGENTS.find(a => a.id === selectedAgent) : null;

  return (
    <div style={{
      minHeight: "100vh", background: "#07070F",
      fontFamily: "'Space Mono', 'Courier New', monospace",
      color: "#e4e4e4",
    }}>
      {/* Header */}
      <div style={{ padding: "20px 28px 0", borderBottom: "1px solid #ffffff10" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, color: "#ffffff40",
              textTransform: "uppercase", marginBottom: 4 }}>
              AxQxOS · WHAM ENGINE
            </div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, letterSpacing: 1,
              color: "#fff", lineHeight: 1 }}>
              AGENTS REGISTRY
            </h1>
            <div style={{ fontSize: 10, color: "#ffffff40", marginTop: 4, letterSpacing: 1 }}>
              v2.0.0 · 6 Boos · Isometric Lattice 2×2×2
            </div>
          </div>
          <div style={{ textAlign: "right", fontSize: 10, color: "#ffffff30", lineHeight: 1.6 }}>
            <div>Particle Model Active</div>
            <div>VH2 ⊗ VH100 → γ</div>
            <div style={{ color: "#3DD9A460" }}>ε₀ = 9.83 SDE</div>
          </div>
        </div>

        {/* Token strip */}
        <div style={{ display: "flex", gap: 12, padding: "10px 0 0", overflowX: "auto" }}>
          {["AXIS","PLUG","TRACE","BLOOM","LUMEN","SOULOS","GLOH","PEACHES"].map(t => (
            <span key={t} style={{ fontSize: 9, padding: "3px 8px",
              border: "1px solid #ffffff20", borderRadius: 2,
              color: "#ffffff50", letterSpacing: 1, whiteSpace: "nowrap" }}>{t}</span>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 0, minHeight: "calc(100vh - 110px)" }}>
        {/* Lattice panel */}
        <div style={{ padding: "20px 16px", borderRight: "1px solid #ffffff10" }}>
          <div style={{ fontSize: 9, letterSpacing: 3, color: "#ffffff30",
            textTransform: "uppercase", marginBottom: 12 }}>Worldline Lattice</div>
          <div style={{ height: 220 }}>
            <LatticeViz agents={AGENTS} activeAgent={activeAgent}
              onSelect={id => { setActiveAgent(id); setSelectedAgent(id); }} />
          </div>
          <div style={{ marginTop: 12, fontSize: 9, color: "#ffffff25", lineHeight: 1.8 }}>
            <div>── active worldline</div>
            <div>· · passive edge</div>
            <div style={{ marginTop: 6, color: "#ffffff35" }}>ρ ≥ 0.60 → active</div>
          </div>
        </div>

        {/* Agent cards grid */}
        <div style={{ padding: "20px", overflowY: "auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
            {AGENTS.map(a => (
              <div key={a.id}
                onClick={() => { setActiveAgent(a.id); setSelectedAgent(a.id); }}
                onMouseEnter={() => setActiveAgent(a.id)}
                onMouseLeave={() => setActiveAgent(null)}
                style={{
                  padding: "14px 16px", borderRadius: 8, cursor: "pointer",
                  background: activeAgent === a.id ? `${a.color}10` : "#0D0D1A",
                  border: `1px solid ${activeAgent === a.id ? a.color + "60" : "#ffffff10"}`,
                  boxShadow: activeAgent === a.id ? `0 0 20px ${a.glow}` : "none",
                  transition: "all 0.18s",
                }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%",
                    background: a.color, boxShadow: `0 0 6px ${a.color}` }} />
                  <span style={{ color: a.color, fontSize: 13, fontWeight: 700,
                    letterSpacing: 1.5 }}>{a.id}</span>
                </div>
                <div style={{ color: "#c0c0c0", fontSize: 10, marginBottom: 6, lineHeight: 1.4 }}>{a.role}</div>
                <div style={{ fontSize: 9, color: "#ffffff30", marginBottom: 4 }}>
                  capsule: <span style={{ color: a.color + "CC" }}>{a.capsule}</span>
                </div>
                <div style={{ fontSize: 9, color: "#ffffff30", marginBottom: 8 }}>
                  particle: <span style={{ color: "#ffffff60" }}>{a.particle}</span>
                </div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {a.token.split("·").map(t => (
                    <span key={t} style={{ fontSize: 8, padding: "2px 5px",
                      background: `${a.color}18`, border: `1px solid ${a.color}40`,
                      borderRadius: 2, color: a.color + "CC" }}>{t}</span>
                  ))}
                </div>
                <div style={{ marginTop: 10, fontSize: 9, color: "#ffffff25",
                  fontFamily: "monospace" }}>[{a.worldline.join(",")}]</div>
              </div>
            ))}
          </div>

          {/* Particle annihilation panel */}
          <div style={{ marginTop: 20, padding: "14px 18px", background: "#0D0D1A",
            border: "1px solid #FF5E5E30", borderRadius: 8 }}>
            <div style={{ fontSize: 9, letterSpacing: 3, color: "#FF5E5E80",
              textTransform: "uppercase", marginBottom: 10 }}>
              Annihilation Event · Phase Change
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr auto 1fr", gap: 8, alignItems: "center" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ color: "#5BB8FF", fontSize: 11, fontWeight: 700 }}>VH2</div>
                <div style={{ color: "#ffffff40", fontSize: 9 }}>electron · matter</div>
                <div style={{ color: "#5BB8FF80", fontSize: 9, fontFamily: "monospace" }}>E=√1536≈39.19</div>
              </div>
              <div style={{ color: "#FF5E5E", fontSize: 16, fontWeight: 700 }}>⊗</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ color: "#FF9999", fontSize: 11, fontWeight: 700, textDecoration: "line-through" }}>VH100</div>
                <div style={{ color: "#ffffff40", fontSize: 9 }}>positron · ai slop</div>
                <div style={{ color: "#FF999980", fontSize: 9, fontFamily: "monospace" }}>E=√512≈22.6</div>
              </div>
              <div style={{ color: "#F5C542", fontSize: 16 }}>→</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ color: "#F5C542", fontSize: 11, fontWeight: 700 }}>γ burst</div>
                <div style={{ color: "#ffffff40", fontSize: 9 }}>ε₀ = 9.83 SDE</div>
                <div style={{ color: "#F5C54280", fontSize: 9, fontFamily: "monospace" }}>seeds all agents</div>
              </div>
            </div>
            <div style={{ marginTop: 10, textAlign: "center", fontSize: 9,
              color: "#ffffff25", letterSpacing: 1 }}>
              repo structure → code execution · Canonical truth, attested and replayable.
            </div>
          </div>
        </div>
      </div>

      {agent && <AgentCard agent={agent} onClose={() => setSelectedAgent(null)} />}
    </div>
  );
}
