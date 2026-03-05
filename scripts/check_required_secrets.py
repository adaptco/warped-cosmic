"""Fail-closed required secret checks for CI pipelines."""
from __future__ import annotations

import argparse
import os


DEFAULT_REQUIRED = ["CODESTRAL_API_KEY"]
PROVIDER_REQUIREMENTS = {
    "claude": ["ANTHROPIC_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "gemini": ["GEMINI_API_KEY"],
    "ollama": [],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check required env secrets")
    parser.add_argument(
        "--required",
        nargs="*",
        default=DEFAULT_REQUIRED,
        help="Required env vars",
    )
    parser.add_argument(
        "--llm-target",
        default=os.getenv("LLM_TARGET", "gemini"),
        help="LLM target provider (claude|openai|gemini|ollama|any).",
    )
    args = parser.parse_args()

    llm_target = str(args.llm_target or "gemini").strip().lower()
    required = list(args.required)
    if llm_target in PROVIDER_REQUIREMENTS:
        required.extend(PROVIDER_REQUIREMENTS[llm_target])
    elif llm_target == "any":
        if not any(os.getenv(name) for names in PROVIDER_REQUIREMENTS.values() for name in names):
            print("Missing provider API key for LLM_TARGET=any:")
            print("- one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY")
            raise SystemExit(1)
    else:
        print(f"Unsupported --llm-target value: {llm_target}")
        raise SystemExit(1)

    required = sorted(set(required))
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Missing required secrets:")
        for item in missing:
            print(f"- {item}")
        raise SystemExit(1)

    print(f"All required secrets present ({len(required)} checked; llm_target={llm_target})")


if __name__ == "__main__":
    main()
