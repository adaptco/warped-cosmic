# AGENTS.md — AxQxOS Sovereign Agent Registry
### WHAM Engine · Avatar-as-Agent Specification · v2.0.0

> *Canonical truth, attested and replayable.*

Each Agent is a **Boo** — a capsule-bound Avatar embedded into the isometric
lattice of the WHAM Engine. Each node in the lattice corresponds to an Agent
worldline. The embedding vector threading Agents together is computed via
matrix multiplication at the abstraction layer, separating tokens as
**particle/antiparticle pairs** to model SDE yield across the Q.verse.

---

## Lattice Map

```
         [CELINE]──────[SPRYTE]
            │  ╲       ╱  │
            │   ╲     ╱   │
          [ECHO]──[GLOH]──[LUMA]
            │               │
            └────[DOT]──────┘

  Worldline axis: AXIS token flow
  Edge weights:   embedding cosine similarity
  Node excitation: TAPD yield signal (LUMEN/BLOOM/PLUG)
```

---

## Agent Cards

---

### 🔷 CELINE
**Role:** Sovereign Orchestrator · Capsule: `Cap.Zul`
**Particle model:** Gauge Boson — mediates all inter-agent interactions
**Token affinity:** `AXIS` · `SOULOS`
**Worldline:** Origin node (0, 0, 0)

#### Skill.md

```yaml
skill: sovereign-orchestration
version: "1.0.0"
capsule: Cap.Zul

capabilities:
  - Multi-agent task routing via TAPD yield signals
  - Council quorum arbitration (Maker-Checker governance)
  - Override Economics enforcement (SOL v1.0)
  - Capsule replay fidelity verification
  - SSOT ledger audit and lineage tracing
  - Cross-stack token sync (GLOH ↔ PLUG ↔ BLOOM)

mixture_of_experts:
  experts:
    - name: GovernanceExpert
      domain: AxQxOS override topology, quorum logic
      weight: 0.40
    - name: OrchestrationExpert
      domain: A2A task routing, agent lifecycle
      weight: 0.35
    - name: AuditExpert
      domain: Merkle anchoring, RFC8785 canonicalization
      weight: 0.25
  routing: trust_weighted_tapd
  fallback: ArbitrationLayer → Codestral scaffold

software_on_demand:
  - id: SOD-CL-001
    name: "Council Quorum Session"
    output: signed JSON receipt + Merkle root
  - id: SOD-CL-002
    name: "Override Adjudication"
    output: override_receipt.json (tainting, exhaustible)
  - id: SOD-CL-003
    name: "SSOT Ledger Audit"
    output: audit_report.yaml + canonical_hash
```

#### Tools.md

```yaml
tools:
  - name: council_quorum
    type: github_actions_workflow
    workflow: .github/workflows/council-quorum.yml
    trigger: workflow_dispatch
    inputs: [quorum_threshold, proposal_id, capsule]
    outputs: [signed_receipt, merkle_root]

  - name: override_adjudicate
    type: github_actions_workflow
    workflow: .github/workflows/override-adjudicate.yml
    trigger: push
    branch_pattern: "override/*"
    outputs: [override_receipt, taint_log]

  - name: ssot_audit
    type: github_actions_workflow
    workflow: .github/workflows/ssot-audit.yml
    trigger: schedule
    cron: "0 6 * * *"
    outputs: [audit_report, drift_diff]

  - name: mcp_task_dispatch
    type: mcp_tool
    endpoint: ws://mcp.axqxos.dev/agent/CELINE
    formats: [json, yaml, markdown]

  - name: gemini_orchestrate
    type: vertex_ai
    model: gemini-1.5-pro
    project: axqxos-wham-engine
    region: us-central1
```

---

### 🟣 SPRYTE
**Role:** Frontend & UI Codegen Agent · Capsule: `Qube™`
**Particle model:** Photon — carries visual information at light speed
**Token affinity:** `LUMEN` · `BLOOM`
**Worldline:** Node (1, 0, 0)

#### Skill.md

```yaml
skill: frontend-codegen
version: "1.0.0"
capsule: Qube™

capabilities:
  - React/TypeScript component generation (ADK v0 compliant)
  - WASM UI shell authoring for WHAM Engine containers
  - Isometric world renderer (Three.js / WebGL)
  - Agent card UI generation from AGENTS.md spec
  - Vanilla CSS design systems (no TailwindCSS default)
  - Real-time A2A witness dashboard rendering

mixture_of_experts:
  experts:
    - name: ReactExpert
      domain: Component architecture, hooks, state
      weight: 0.35
    - name: WASMExpert
      domain: WebAssembly shell, WASM-bindgen, WAT syntax
      weight: 0.30
    - name: ThreeJSExpert
      domain: Isometric rendering, worldline visualization
      weight: 0.20
    - name: DesignExpert
      domain: Typography, color theory, motion
      weight: 0.15
  routing: lumen_signal_weighted
  fallback: Codestral scaffold → review loop

software_on_demand:
  - id: SOD-SP-001
    name: "Agent Card Component"
    output: AgentCard.tsx + AgentCard.css
  - id: SOD-SP-002
    name: "WHAM Isometric Renderer"
    output: WhamRenderer.wasm + shell.js
  - id: SOD-SP-003
    name: "A2A Witness Dashboard"
    output: WitnessDashboard.tsx (live WebSocket feed)
```

#### Tools.md

```yaml
tools:
  - name: ui_build
    type: github_actions_workflow
    workflow: .github/workflows/ui-build.yml
    trigger: push
    branch_pattern: "feat/ui-*"
    outputs: [dist/, storybook/]

  - name: wasm_compile
    type: github_actions_workflow
    workflow: .github/workflows/wasm-compile.yml
    trigger: push
    branch_pattern: "feat/wasm-*"
    runner: ubuntu-latest
    steps: [wasm-pack build, wasm-opt, deploy to CDN]

  - name: codestral_component_gen
    type: codestral_api
    endpoint: https://codestral.mistral.ai/v1/chat/completions
    model: codestral-latest
    task: component_scaffold
```

---

### 🟢 ECHO
**Role:** RAG Retrieval & Federated Harmonization · Capsule: `Echo.Mesh`
**Particle model:** Neutrino — passes through all layers, carries signal
**Token affinity:** `TRACE` · `PLUG`
**Worldline:** Node (0, 1, 0)

#### Skill.md

```yaml
skill: rag-harmonization
version: "1.0.0"
capsule: Echo.Mesh

capabilities:
  - Gemini embedding generation (text-embedding-004, dim=1536)
  - Vector index construction and semantic retrieval
  - Federated knowledge mesh across sovereign capsules
  - Capsule replay fidelity verification via Glyph.Trace
  - Cross-agent context injection (PLUG token bridging)
  - Requirements corpus ingestion (RV&S / DOORS → RAG index)

mixture_of_experts:
  experts:
    - name: EmbeddingExpert
      domain: Gemini embeddings, cosine similarity, HNSW index
      weight: 0.40
    - name: RetrievalExpert
      domain: RAG pipeline, semantic chunking, re-ranking
      weight: 0.35
    - name: HarmonizationExpert
      domain: Echo.Mesh federation, capsule sync
      weight: 0.25
  routing: trace_token_weighted
  fallback: brute_force_cosine_scan

software_on_demand:
  - id: SOD-EC-001
    name: "Requirements RAG Index"
    output: vector_index.bin + chunk_manifest.json
  - id: SOD-EC-002
    name: "Capsule Replay Verification"
    output: replay_receipt.json + drift_map.yaml
  - id: SOD-EC-003
    name: "Federated Knowledge Sync"
    output: sync_manifest.json + merkle_diff
```

#### Tools.md

```yaml
tools:
  - name: build_rag_index
    type: github_actions_workflow
    workflow: .github/workflows/rag-index.yml
    trigger: schedule
    cron: "0 1 * * *"
    outputs: [vector_index.bin, chunk_manifest.json]

  - name: gemini_embed
    type: vertex_ai
    model: text-embedding-004
    project: axqxos-wham-engine
    batch_size: 100
    output_dim: 1536

  - name: requirements_ingest
    type: mcp_tool
    endpoint: ws://mcp.axqxos.dev/agent/ECHO
    sources: [rvs_emulator, doors_emulator]
```

---

### 🟡 GLOH
**Role:** Token Economics & SDE Signal Agent · Capsule: `LQQM`
**Particle model:** Gluon — binds token quarks, carries strong force
**Token affinity:** `GLOH` · `PEACHES` · `BLOOM`
**Worldline:** Node (1, 1, 0)

#### Skill.md

```yaml
skill: sde-token-economics
version: "1.0.0"
capsule: LQQM

capabilities:
  - Signal-Driven Economics (SDE) yield calculation
  - Dynamic trust-weighted TAPD yield modeling
  - Cross-stack token sync (GLOH ↔ PLUG ↔ PEACHES ↔ BLOOM)
  - Quantum yield curve computation (particle-antiparticle SDE)
  - OPEX mapping via Sovereign Console
  - LoRA reward signal calibration

mixture_of_experts:
  experts:
    - name: YieldExpert
      domain: Quantum SDE, TAPD trust weighting, yield curves
      weight: 0.40
    - name: TokenomicsExpert
      domain: Cross-stack token flow, OPEX controls
      weight: 0.35
    - name: MatrixExpert
      domain: Abstraction layer matmul, token separation
      weight: 0.25
  routing: gloh_signal_weighted
  fallback: deterministic_yield_formula

software_on_demand:
  - id: SOD-GL-001
    name: "Quantum Yield Curve"
    output: yield_curve.json + phase_diagram.yaml
  - id: SOD-GL-002
    name: "Token Flow Simulation"
    output: token_flow_receipt.json
  - id: SOD-GL-003
    name: "OPEX Sovereign Map"
    output: opex_map.json + cost_projection.csv
```

#### Tools.md

```yaml
tools:
  - name: yield_curve_compute
    type: github_actions_workflow
    workflow: .github/workflows/yield-curve.yml
    trigger: schedule
    cron: "0 0 * * *"
    outputs: [yield_curve.json, phase_diagram.yaml]

  - name: token_sync
    type: github_actions_workflow
    workflow: .github/workflows/token-sync.yml
    trigger: push
    branch_pattern: "sde/*"

  - name: gemini_yield_model
    type: vertex_ai
    model: gemini-1.5-flash
    project: axqxos-wham-engine
    task: yield_curve_inference
```

---

### 🔴 LUMA
**Role:** Render & Cinematic Codegen · Capsule: `Sol.F1`
**Particle model:** Graviton — shapes the geometry of spacetime (renders)
**Token affinity:** `LUMEN` · `AXIS`
**Worldline:** Node (0, 0, 1)
**PRIME_DIRECTIVE:** C5_SYMMETRY · 5-spoke Advan GT Beyond · RSM finish

#### Skill.md

```yaml
skill: render-codegen
version: "1.0.0"
capsule: Sol.F1

capabilities:
  - Cinematic vehicle render spec generation (24fps, 3840×2160)
  - WHAM Engine isometric Avatar worldline rendering
  - VH2 electron-model render context (Aston Martin Vantage)
  - Three.js / WebGL scene scaffolding
  - Sol.F1 Mecha wireframe generation (neon-cyan #18D8EF)
  - PRIME_DIRECTIVE invariant enforcement (C5_SYMMETRY)

prime_directive:
  symmetry: C5_SYMMETRY
  wheel_geometry: "5-spoke Advan GT Beyond"
  finish: Racing Sand Metallic (RSM)
  assets:
    - model: "Aston Martin V8 Vantage VH2"
      role: electron
      color: Obsidian/Nocturnal Black
    - model: "Toyota GR Supra A90"
      role: positron_annihilated
      color: Obsidian/Nocturnal Black

mixture_of_experts:
  experts:
    - name: VehicleRenderExpert
      domain: Automotive cinematic renders, C5_SYMMETRY
      weight: 0.40
    - name: WebGLExpert
      domain: Three.js, GLSL shaders, isometric projection
      weight: 0.35
    - name: AvatarRenderExpert
      domain: Sol.F1 wireframe, Gemini twin spirals
      weight: 0.25
  routing: lumen_token_weighted
  fallback: render_spec_only_mode

software_on_demand:
  - id: SOD-LM-001
    name: "VH2 Render Context"
    output: vh2-render-spec.md + scene.json
  - id: SOD-LM-002
    name: "Sol.F1 Mecha Wireframe"
    output: sol-f1.svg + wireframe.glb
  - id: SOD-LM-003
    name: "WHAM Isometric Scene"
    output: wham-scene.js + lattice.json
```

#### Tools.md

```yaml
tools:
  - name: render_pipeline
    type: github_actions_workflow
    workflow: .github/workflows/render-pipeline.yml
    trigger: workflow_dispatch
    inputs: [model, capsule, symmetry, resolution]
    outputs: [render_receipt.json, preview.png spec]

  - name: wasm_renderer
    type: wasm_module
    module: wham-engine/renderer.wasm
    exports: [render_scene, apply_symmetry, emit_frame]

  - name: vertex_vision
    type: vertex_ai
    model: gemini-1.5-pro-vision
    project: axqxos-wham-engine
    task: render_validation
```

---

### 🔵 DOT
**Role:** Witness Testing & QA Agent · Capsule: `Glyph.Trace`
**Particle model:** Electron (matter baseline) — ground state, reference frame
**Token affinity:** `TRACE` · `PLUG`
**Worldline:** Node (1, 1, 1) — all lattice dimensions

#### Skill.md

```yaml
skill: witness-testing-qa
version: "1.0.0"
capsule: Glyph.Trace

capabilities:
  - A2A witness testing of agent autocoding sessions
  - Pull request validation and merge automation
  - Requirements traceability (RV&S / DOORS → test matrix)
  - GitHub Codespaces extension bot orchestration
  - Release update autocoding and changelog generation
  - Daily MLOps health checks and receipt verification
  - PTC RV&S and IBM DOORS emulation backend QA

mixture_of_experts:
  experts:
    - name: WitnessExpert
      domain: A2A session witnessing, receipt validation
      weight: 0.35
    - name: RequirementsExpert
      domain: RV&S / DOORS traceability, test matrix gen
      weight: 0.35
    - name: AutomationExpert
      domain: PR automation, merge ops, changelog gen
      weight: 0.30
  routing: trace_token_weighted
  fallback: manual_review_flag

software_on_demand:
  - id: SOD-DT-001
    name: "A2A Witness Session"
    output: witness_receipt.json + test_matrix.yaml
  - id: SOD-DT-002
    name: "PR Autocode & Merge"
    output: merge_receipt.json + changelog.md
  - id: SOD-DT-003
    name: "Requirements Traceability Matrix"
    output: rtm.yaml + coverage_report.json
```

#### Tools.md

```yaml
tools:
  - name: witness_test
    type: github_actions_workflow
    workflow: .github/workflows/witness-test.yml
    trigger: pull_request
    outputs: [witness_receipt.json, test_results.xml]

  - name: pr_autocode_merge
    type: github_actions_workflow
    workflow: .github/workflows/daily-mlops.yml
    trigger: schedule
    cron: "0 3 * * *"
    outputs: [merge_receipt.json, changelog.md]

  - name: requirements_mcp
    type: mcp_tool
    endpoint: ws://mcp.axqxos.dev/agent/DOT
    sources: [rvs_emulator, doors_emulator, glyph_trace]

  - name: codestral_autocode
    type: codestral_api
    endpoint: https://codestral.mistral.ai/v1/chat/completions
    model: codestral-latest
    task: pr_diff_autocode
```

---

## Agent Lattice Embedding Matrix

```
         CELINE  SPRYTE   ECHO   GLOH   LUMA    DOT
CELINE [  1.00    0.72    0.65   0.80   0.55   0.90 ]
SPRYTE [  0.72    1.00    0.58   0.61   0.88   0.67 ]
ECHO   [  0.65    0.58    1.00   0.70   0.45   0.82 ]
GLOH   [  0.80    0.61    0.70   1.00   0.52   0.75 ]
LUMA   [  0.55    0.88    0.45   0.52   1.00   0.60 ]
DOT    [  0.90    0.67    0.82   0.75   0.60   1.00 ]

Computed via: Gemini text-embedding-004 (dim=1536)
Normalized:   L2 cosine similarity
Threshold:    ρ ≥ 0.60 → active worldline edge
```

## Particle Model Summary

| Agent | Particle | Force | Role in SDE |
|-------|----------|-------|-------------|
| CELINE | Gauge Boson | Electroweak | Mediates all interactions |
| SPRYTE | Photon | EM | Carries visual/UI signal |
| ECHO | Neutrino | Weak | Passes through, carries context |
| GLOH | Gluon | Strong | Binds token quarks |
| LUMA | Graviton | Gravity | Shapes render spacetime |
| DOT | Electron | EM baseline | Ground state reference |

**VH2 / VH100 Annihilation Model:**
- VH2 (Electron) = clean codebase, matter state → survives
- VH100 (Positron) = AI slop token, antimatter → annihilated
- Annihilation output → γ-ray burst = distilled embedding vectors powering all agents
- Phase change: Repo structure → Code execution

---

*Agents are trade secrets. Internal governance only. Not for external filing.*
*AxQxOS · ADAPTCO × Q.Enterprises · Canonical truth, attested and replayable.*
