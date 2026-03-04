"""Digital Brain Agent System — CLI entry point.

Starts the MCP server, initializes the Digital Brain filing system,
and optionally runs the agentic swarm from the command line.
"""

from __future__ import annotations

import argparse
import json
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from digital_brain.brain import DigitalBrain
from digital_brain.thread import DigitalThread
from middleware.wave_runtime import WaveformRuntime
from physics_search.engine import PhysicsSearchEngine
from swarm.swarm_runner import SwarmRunner


def _seed_brain(brain: DigitalBrain, search_engine: PhysicsSearchEngine) -> None:
    """Seed the brain with starter knowledge repos."""
    repos = [
        ("orchestration", "systems", "Multi-agent pipeline orchestration patterns"),
        ("physics", "science", "Physics-informed neural networks and wave models"),
        ("git-ops", "devops", "Git merge workflows and commit automation"),
        ("vector-search", "ml", "Vector embeddings and semantic search"),
        ("mcp-protocol", "protocol", "Model Context Protocol for agent-to-agent comms"),
    ]
    for name, domain, desc in repos:
        repo = brain.create_repo(name, domain, desc)
        entry = brain.file_knowledge(
            repo.repo_id, desc, source="seed", tags=[domain]
        )
        search_engine.index_entry(entry)

    print(f"[OK] Seeded {brain.repo_count} repos, {brain.entry_count} entries")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Digital Brain Agent System",
    )
    sub = parser.add_subparsers(dest="command")

    # serve
    serve_cmd = sub.add_parser("serve", help="Start the MCP server")

    # run
    run_cmd = sub.add_parser("run", help="Run the swarm on a prompt")
    run_cmd.add_argument("prompt", help="The prompt to process")

    # status
    sub.add_parser("status", help="Show system status")

    args = parser.parse_args()

    brain = DigitalBrain()
    thread = DigitalThread()
    runtime = WaveformRuntime()
    search_engine = PhysicsSearchEngine()
    _seed_brain(brain, search_engine)

    runner = SwarmRunner(brain, thread, runtime, search_engine)

    if args.command == "serve":
        print("Starting Digital Brain MCP Server...")
        from server.mcp_server import run_server
        run_server()

    elif args.command == "run":
        print(f"Running swarm on prompt: {args.prompt!r}")
        result = runner.run(args.prompt)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "status":
        state = runner.get_state()
        print(json.dumps(state, indent=2, default=str))
        print(f"\nBrain repos: {brain.repo_count}")
        print(f"Brain entries: {brain.entry_count}")
        print(f"Thread nodes: {thread.node_count}")
        print(f"Search index: {search_engine.index_size}")
        print(f"Runtime states: {runtime.active_states}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
