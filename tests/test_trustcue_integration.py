"""Tests for the TrustCue persona and bounded ChurnCue MCP bootstrap."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from coworker.mcp import load_mcp_servers
from coworker.personas.registry import PersonaRegistry
from coworker.secrets import SecretStore

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = REPO_ROOT / "integrations" / "trustcue" / "bootstrap.py"
EXPECTED_TOOLS = [
    "health_check",
    "load_demo_dataset",
    "profile_dataset",
    "train_models",
    "score_customers",
    "compare_weekly_risk",
    "explain_risk",
    "generate_rescue_report",
]


def load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("trustcue_bootstrap", BOOTSTRAP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_trustcue_persona_is_governed():
    registry = PersonaRegistry()
    entry = registry.get("trustcue")
    assert entry is not None
    assert entry.family == "knowledge"
    assert entry.tools == ["files", "search", "todo"]

    agent = registry.agent("trustcue")
    assert agent.messaging is True
    assert agent.connectors is True
    assert "Use ChurnCue MCP tools" in agent.system_prompt
    assert "explicit human approval" in agent.system_prompt
    assert "Prepare external communications as drafts only" in agent.system_prompt


def test_bootstrap_configures_bounded_mcp_and_persona(tmp_path, monkeypatch):
    module = load_bootstrap_module()
    monkeypatch.setenv("COWORKER_STATE_DIR", str(tmp_path / "state"))
    workspace = tmp_path / "workspace"

    config_path, persona_path, prompt_path = module.configure_workspace(
        workspace=workspace,
        churncue_url="http://localhost:8000/mcp",
        force=False,
    )

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    churncue = raw["mcpServers"]["churncue"]
    assert churncue["type"] == "streamable-http"
    assert churncue["url"] == "http://localhost:8000/mcp"
    assert churncue["include_tools"] == EXPECTED_TOOLS
    assert churncue["requires_approval"] is False

    servers = {
        server.name: server
        for server in load_mcp_servers(workspace, secrets=SecretStore())
    }
    server = servers["churncue"]
    assert server.transport == "http"
    assert server.include_tools == EXPECTED_TOOLS
    assert server.requires_approval is False

    persona_state = json.loads(persona_path.read_text(encoding="utf-8"))
    assert persona_state["enabled"]["trustcue"] is True
    assert persona_state["surfaced"]["trustcue"] is True
    assert persona_state["default"] == "trustcue"

    prompt = prompt_path.read_text(encoding="utf-8")
    assert "Prepare, but do not send" in prompt
    assert "manager approval" in prompt


def test_bootstrap_preserves_unrelated_servers_and_preferences(tmp_path):
    module = load_bootstrap_module()
    workspace = tmp_path / "workspace"
    coworker_dir = workspace / ".coworker"
    coworker_dir.mkdir(parents=True)

    (coworker_dir / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "docs": {"type": "http", "url": "https://example.test/mcp"}
                }
            }
        ),
        encoding="utf-8",
    )
    (coworker_dir / "personas.json").write_text(
        json.dumps(
            {
                "enabled": {"ops": True},
                "surfaced": {"ops": True},
                "default": "ops",
            }
        ),
        encoding="utf-8",
    )

    module.configure_workspace(
        workspace=workspace,
        churncue_url="http://localhost:8000/mcp",
        force=False,
    )

    mcp = json.loads((coworker_dir / "mcp.json").read_text(encoding="utf-8"))
    assert "docs" in mcp["mcpServers"]
    assert "churncue" in mcp["mcpServers"]

    personas = json.loads(
        (coworker_dir / "personas.json").read_text(encoding="utf-8")
    )
    assert personas["enabled"]["ops"] is True
    assert personas["enabled"]["trustcue"] is True
    assert personas["default"] == "trustcue"


def test_bootstrap_requires_force_to_replace_churncue(tmp_path):
    module = load_bootstrap_module()
    workspace = tmp_path / "workspace"

    module.configure_workspace(
        workspace=workspace,
        churncue_url="http://localhost:8000/mcp",
        force=False,
    )

    with pytest.raises(FileExistsError):
        module.configure_workspace(
            workspace=workspace,
            churncue_url="http://localhost:9000/mcp",
            force=False,
        )

    module.configure_workspace(
        workspace=workspace,
        churncue_url="http://localhost:9000/mcp",
        force=True,
    )
    raw = json.loads(
        (workspace / ".coworker" / "mcp.json").read_text(encoding="utf-8")
    )
    assert raw["mcpServers"]["churncue"]["url"] == "http://localhost:9000/mcp"
