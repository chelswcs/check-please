#!/usr/bin/env python3
"""Claude Code SessionEnd hook entrypoint for token receipt."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from check_please.hooks import build_session_end_system_message  # noqa: E402
from check_please.models import DEFAULT_PRICING  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a check-please systemMessage payload for Claude SessionEnd hooks.")
    parser.add_argument("--usage-path", type=Path, help="Override Claude usage-data JSON path.")
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING)
    parser.add_argument("--width", type=int, default=48)
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    hook_input = json.loads(raw) if raw else {}
    usage_override = args.usage_path
    if usage_override is None:
        usage_env = os.environ.get("TOKEN_RECEIPT_CLAUDE_USAGE_PATH")
        if usage_env:
            usage_override = Path(usage_env)

    try:
        payload = build_session_end_system_message(
            hook_input=hook_input,
            usage_path=usage_override,
            pricing_path=args.pricing,
            width=args.width,
        )
    except Exception as exc:  # pragma: no cover - defensive hook fallback
        payload = {
            "continue": True,
            "suppressOutput": True,
            "systemMessage": f"Check Please hook failed: {exc}",
        }

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
