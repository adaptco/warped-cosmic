"""Sign and verify pipeline receipts with deterministic HMAC signatures."""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path


def _canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign(payload: dict, key: str) -> str:
    digest = hmac.new(key.encode("utf-8"), _canonical_bytes(payload), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sign AxQxOS receipt files")
    parser.add_argument("input", help="Path to JSON receipt")
    parser.add_argument("--output", help="Path to write signed receipt")
    parser.add_argument("--key-env", default="PIPELINE_SIGNING_KEY", help="Environment variable containing HMAC key")
    args = parser.parse_args()

    key = os.getenv(args.key_env)
    if not key:
        raise SystemExit(f"Missing signing key in env var: {args.key_env}")

    in_path = Path(args.input)
    data = json.loads(in_path.read_text(encoding="utf-8"))

    unsigned = dict(data)
    unsigned.pop("signature", None)
    data["signature"] = sign(unsigned, key)

    out_path = Path(args.output) if args.output else in_path
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Signed: {out_path}")


if __name__ == "__main__":
    main()
