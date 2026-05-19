#!/usr/bin/env python3
"""Remove Claude Code SessionEnd auto-trigger for token receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from check_please.hooks import DEFAULT_SETTINGS_PATH, uninstall_session_end_hook  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove Claude Code SessionEnd auto-trigger for token receipt.")
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS_PATH)
    args = parser.parse_args()

    result = uninstall_session_end_hook(settings_path=args.settings)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
