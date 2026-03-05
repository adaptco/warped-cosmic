# Boo Agent Capability Matrix

Boo agents are AxQxOS functional agents. Each is a named persona bound to a skill domain.
They are **trade secrets** — referenced by name only, never exposed externally.

## Capability Matrix

| Boo | Primary Domain | RASIC Default | LLM Preference | MCP Role |
|-----|---------------|---------------|----------------|----------|
| Celine | Planning, PRD synthesis, PM decisions | A (Accountable) | claude | Strategy planner |
| Spryte | Frontend, UI/UX artifact generation | R (Responsible) | any | Code generator |
| Echo | Inter-agent messaging, webhook relay | S (Supportive) | any | Message broker |
| Gloh | Data normalization, RAG, vector ops | R (Responsible) | gemini/ollama | Retrieval agent |
| Luma | Evaluation, QA, receipt attestation | A (Accountable) | claude | Quality gate |
| Dot | CI/CD, infra, GitHub Actions | R (Responsible) | any | Automation runner |

## Binding Rules

1. Every task node MUST have at least one R and one A Boo binding
2. Echo is always S or I on every task (relay awareness)
3. Luma is always A on any task that produces a receipt
4. Dot is always R on any task that touches `.github/workflows/`
5. Celine is always A on Phase 0 (intake) and Phase 7 (implementation plan)
6. Gloh is always R on any task involving RAG, vector stores, or data normalization
7. Spryte is always R on any task producing frontend or UI artifacts

## Null Binding
Set `boo_binding: null` only for external/third-party agent tasks where no Boo owns the domain.
Always add a comment explaining why.

## Multi-Binding
A task may have multiple Boos. List as array: `["Dot", "Luma"]`.
The first entry is primary R or A; subsequent entries are supporting roles.
