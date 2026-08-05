#!/usr/bin/env python3
"""Configure a workspace to use the local ChurnCue MCP server with OpenWorker.

The script preserves unrelated MCP server entries and atomically writes the
workspace-scoped `.coworker/mcp.json` file. It never stores API keys.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

APPROVED_TOOLS = [
    "health_check",
    "load_demo_dataset",
    "profile_dataset",
    "train_models",
    "score_customers",
    "compare_weekly_risk",
    "explain_risk",
    "generate_rescue_report",
]

DEMO_PROMPT = """Run the complete weekly retention workflow on the approved demo dataset.

Requirements:
1. Confirm ChurnCue health.
2. Load and profile the demo dataset.
3. Train or select the recommended deterministic model.
4. Score customers and compare weekly risk.
5. Show the top five accounts by revenue-weighted risk.
6. Explain each account using only evidence returned by ChurnCue.
7. Generate the rescue report.
8. Prepare, but do not send, an internal Slack draft for manager approval.
9. Clearly state data-quality and model limitations.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure an OpenWorker workspace for the TrustCue demo."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.home() / "trustcue-workspace",
        help="OpenWorker workspace directory (default: ~/trustcue-workspace).",
    )
    parser.add_argument(
        "--churncue-url",
        default="http://localhost:8000/mcp",
        help="ChurnCue Streamable HTTP MCP endpoint.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing MCP entry named 'churncue'.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def configure_workspace(workspace: Path, churncue_url: str, force: bool) -> Path:
    workspace = workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    config_path = workspace / ".coworker" / "mcp.json"
    config = read_json(config_path)
    servers = config.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"'mcpServers' must be an object in {config_path}")

    if "churncue" in servers and not force:
        raise FileExistsError(
            "The workspace already has an MCP server named 'churncue'. "
            "Use --force to replace only that entry."
        )

    servers["churncue"] = {
        "type": "streamable-http",
        "url": churncue_url,
        "enabled": True,
        "include_tools": APPROVED_TOOLS,
        # ChurnCue tools calculate and prepare reports but do not send outbound
        # messages. OpenWorker connector writes remain approval-gated.
        "requires_approval": False,
    }
    write_json_atomic(config_path, config)

    prompt_path = workspace / "TRUSTCUE_DEMO_PROMPT.md"
    prompt_path.write_text(DEMO_PROMPT, encoding="utf-8")
    return config_path


def main() -> int:
    args = parse_args()
    try:
        config_path = configure_workspace(
            workspace=args.workspace,
            churncue_url=args.churncue_url,
            force=args.force,
        )
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"TrustCue bootstrap failed: {exc}", file=sys.stderr)
        return 1

    workspace = args.workspace.expanduser().resolve()
    print("TrustCue workspace configured successfully.")
    print(f"Workspace: {workspace}")
    print(f"MCP config: {config_path}")
    print(f"Demo prompt: {workspace / 'TRUSTCUE_DEMO_PROMPT.md'}")
    print("Next: start ChurnCue, start OpenWorker with this workspace, select the TrustCue persona, and paste the demo prompt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
