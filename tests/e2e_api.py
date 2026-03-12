"""E2E API smoke tests — run against a live Docker stack.

Usage:
    docker compose up -d --build
    python tests/e2e_api.py
    docker compose down -v
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8100"


def _get(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def test_health():
    data = _get("/health")
    assert data["status"] == "ok", f"Health failed: {data}"
    assert data["brain_repos"] >= 5, f"Expected >= 5 repos, got {data['brain_repos']}"
    print(f"  [PASS] /health — repos={data['brain_repos']}, state={data['swarm_state']}")


def test_brain_search():
    data = _post("/brain/search", {"query": "orchestration", "top_k": 3})
    assert "results" in data, f"Missing results: {data}"
    assert len(data["results"]) > 0, "No search results returned"
    print(f"  [PASS] /brain/search — {len(data['results'])} results")


def test_brain_file():
    data = _post("/brain/file", {
        "repo_name": "e2e-test",
        "domain": "testing",
        "content": "E2E test content for validation",
    })
    assert "repo_id" in data, f"Missing repo_id: {data}"
    assert "entry_id" in data, f"Missing entry_id: {data}"
    print(f"  [PASS] /brain/file — repo={data['repo_id'][:8]}...")


def test_swarm_status():
    data = _get("/swarm/status")
    assert "state" in data, f"Missing state: {data}"
    print(f"  [PASS] /swarm/status — state={data['state']}")


def test_swarm_dispatch():
    data = _post("/swarm/dispatch", {"prompt": "E2E test: build feature X"})
    assert "pipeline" in data, f"Missing pipeline: {data}"
    assert data["total_commits"] >= 1, f"Expected commits, got {data['total_commits']}"
    print(f"  [PASS] /swarm/dispatch — commits={data['total_commits']}, state={data['final_state']}")


def test_commit_create():
    data = _post("/commit/create", {
        "message": "E2E test commit",
        "files": "test.py,utils.py",
    })
    assert data["status"] == "created", f"Commit failed: {data}"
    print(f"  [PASS] /commit/create — id={data['commit_id'][:8]}...")


def test_agents():
    data = _get("/agents")
    assert "agents" in data, f"Missing agents: {data}"
    assert "runtime_product_delivery" in data, f"Missing runtime schema: {data}"

    delivery = data["runtime_product_delivery"]
    assert delivery["schema"] == "AxQxOS/RuntimeProductDelivery/v1", delivery
    assert delivery["sources"]["agent_registry_path"] == "WHAM-Agents-Dashboard/AGENTS.md", delivery
    assert delivery["sources"]["skill_registry_path"] == "Skills/SKILL.md", delivery

    names = [a["agent_name"] for a in data["agents"]]
    assert "digital_brain" in names, f"Missing digital_brain agent: {names}"
    digital_brain = next(a for a in data["agents"] if a["agent_name"] == "digital_brain")
    assert digital_brain["runtime_binding"]["boo_binding"] == "ECHO", digital_brain
    print(f"  [PASS] /agents — {len(data['agents'])} agents registered")


def test_thread_stitch():
    data = _post("/thread/stitch", {
        "source_repo": "repo-a",
        "target_repo": "repo-b",
        "summary": "E2E cross-link",
    })
    assert "node_id" in data, f"Missing node_id: {data}"
    print(f"  [PASS] /thread/stitch — node={data['node_id'][:8]}...")


def main():
    tests = [
        test_health,
        test_brain_search,
        test_brain_file,
        test_swarm_status,
        test_swarm_dispatch,
        test_commit_create,
        test_agents,
        test_thread_stitch,
    ]

    print("=== Digital Brain E2E API Tests ===\n")
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except (AssertionError, urllib.error.URLError) as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    if failed:
        sys.exit(1)
    print("All E2E tests passed!")


if __name__ == "__main__":
    main()
