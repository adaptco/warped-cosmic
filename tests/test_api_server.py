"""API tests for the production FastAPI surface."""

from __future__ import annotations

import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_server import app


def test_agents_endpoint_exposes_runtime_product_delivery_schema() -> None:
    with TestClient(app) as client:
        response = client.get("/agents")

    assert response.status_code == 200
    payload = response.json()

    assert "agents" in payload
    assert "runtime_product_delivery" in payload

    delivery = payload["runtime_product_delivery"]
    assert delivery["schema"] == "AxQxOS/RuntimeProductDelivery/v1"
    assert delivery["sources"]["agent_registry_path"] == "WHAM-Agents-Dashboard/AGENTS.md"
    assert delivery["sources"]["skill_registry_path"] == "Skills/SKILL.md"
    assert delivery["sources"]["e2e_contract_path"] == "tests/e2e_api.py"

    digital_brain = next(agent for agent in payload["agents"] if agent["agent_name"] == "digital_brain")
    assert digital_brain["runtime_binding"]["boo_binding"] == "ECHO"
    assert digital_brain["runtime_binding"]["delivery_schema"] == delivery["schema"]
