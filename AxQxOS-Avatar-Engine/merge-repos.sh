#!/usr/bin/env bash
# ============================================================
# AxQxOS Avatar Engine — Sovereign Repo Merger
# merge-repos.sh  |  v1.0.0
# Canonical truth, attested and replayable.
# ============================================================
set -euo pipefail
IFS=$'\n\t'

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
MERGE_BRANCH="merge/avatar-engine-${TIMESTAMP}"
COMMIT_MSG="chore(merge): sovereign multi-repo consolidation [${TIMESTAMP}]"
LOG_FILE="logs/merge-${TIMESTAMP}.log"
CANONICAL_REMOTE="origin"

# ── Repo manifest ─────────────────────────────────────────
# FORMAT: "local_path|remote_url|branch"
REPOS=(
  "subtrees/a2a-mcp|git@github.com:eqhsp/a2a-mcp.git|main"
  "subtrees/sovereignty-chain|git@github.com:eqhsp/sovereignty-chain.git|main"
  "subtrees/avatar-system|git@github.com:eqhsp/avatar-system.git|main"
  "subtrees/adk-v0|git@github.com:eqhsp/adk-v0.git|main"
  "subtrees/mesh|git@github.com:eqhsp/mesh.git|main"
  "subtrees/gemini-95|git@github.com:eqhsp/gemini-95.git|main"
)

# ── Guard checks ──────────────────────────────────────────
require_cmd() { command -v "$1" &>/dev/null || { echo "❌ Required: $1"; exit 1; }; }
require_cmd git
require_cmd jq

mkdir -p logs

echo "═══════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "  AxQxOS Sovereign Repo Merger" | tee -a "$LOG_FILE"
echo "  ${TIMESTAMP}" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════" | tee -a "$LOG_FILE"

# ── Ensure clean working tree ─────────────────────────────
if [[ -n "$(git status --porcelain)" ]]; then
  echo "❌ Working tree is dirty. Commit or stash before merging." | tee -a "$LOG_FILE"
  exit 1
fi

# ── Create merge branch ───────────────────────────────────
git checkout -b "$MERGE_BRANCH" 2>&1 | tee -a "$LOG_FILE"

RECEIPT_ENTRIES=()

# ── Merge each repo as subtree ────────────────────────────
for entry in "${REPOS[@]}"; do
  IFS='|' read -r local_path remote_url branch <<< "$entry"
  remote_name=$(basename "$local_path")

  echo "" | tee -a "$LOG_FILE"
  echo "── Merging: ${remote_name} ─────────────────────" | tee -a "$LOG_FILE"
  echo "   Remote : ${remote_url}" | tee -a "$LOG_FILE"
  echo "   Branch : ${branch}" | tee -a "$LOG_FILE"
  echo "   Target : ${local_path}" | tee -a "$LOG_FILE"

  # Add remote if not already present
  if ! git remote get-url "$remote_name" &>/dev/null; then
    git remote add "$remote_name" "$remote_url" 2>&1 | tee -a "$LOG_FILE"
  fi

  git fetch "$remote_name" "$branch" 2>&1 | tee -a "$LOG_FILE"

  # Subtree add or pull
  if [[ -d "$local_path" ]]; then
    git subtree pull --prefix="$local_path" "$remote_name" "$branch" --squash \
      -m "subtree(${remote_name}): pull ${branch} [${TIMESTAMP}]" 2>&1 | tee -a "$LOG_FILE"
  else
    git subtree add --prefix="$local_path" "$remote_name" "$branch" --squash \
      -m "subtree(${remote_name}): initial add [${TIMESTAMP}]" 2>&1 | tee -a "$LOG_FILE"
  fi

  HEAD_SHA=$(git rev-parse "${remote_name}/${branch}")
  RECEIPT_ENTRIES+=("{\"repo\":\"${remote_name}\",\"remote\":\"${remote_url}\",\"branch\":\"${branch}\",\"head\":\"${HEAD_SHA}\",\"prefix\":\"${local_path}\"}")

  echo "   ✓ HEAD: ${HEAD_SHA}" | tee -a "$LOG_FILE"
done

# ── Emit merge receipt (JSON) ─────────────────────────────
RECEIPT_FILE="manifests/merge-receipt-${TIMESTAMP}.json"
ENTRIES_JSON=$(IFS=','; echo "${RECEIPT_ENTRIES[*]}")

cat > "$RECEIPT_FILE" <<EOF
{
  "schema": "AxQxOS/MergeReceipt/v1",
  "timestamp": "${TIMESTAMP}",
  "branch": "${MERGE_BRANCH}",
  "repos": [${ENTRIES_JSON}],
  "canonical": "Canonical truth, attested and replayable."
}
EOF

git add "$RECEIPT_FILE" 2>&1 | tee -a "$LOG_FILE"
git add "$LOG_FILE"     2>&1 | tee -a "$LOG_FILE"

# ── Single canonical commit ───────────────────────────────
git commit -S -m "$COMMIT_MSG

Receipt: ${RECEIPT_FILE}
Repos merged: ${#REPOS[@]}
Timestamp: ${TIMESTAMP}
" 2>&1 | tee -a "$LOG_FILE"

FINAL_SHA=$(git rev-parse HEAD)
echo "" | tee -a "$LOG_FILE"
echo "✅ Merge complete." | tee -a "$LOG_FILE"
echo "   Branch : ${MERGE_BRANCH}" | tee -a "$LOG_FILE"
echo "   Commit : ${FINAL_SHA}" | tee -a "$LOG_FILE"
echo "   Receipt: ${RECEIPT_FILE}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Next: git push ${CANONICAL_REMOTE} ${MERGE_BRANCH} && open PR" | tee -a "$LOG_FILE"
