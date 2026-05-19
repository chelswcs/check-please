#!/usr/bin/env python3
"""Install Claude Code SessionEnd auto-trigger for token receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from check_please.hooks import DEFAULT_SETTINGS_PATH, install_session_end_hook  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Claude Code SessionEnd auto-trigger for token receipt.")
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS_PATH)
    parser.add_argument("--hook-root", type=Path, help="Override the check-please runtime root used in the hook command.")
    parser.add_argument("--python-bin", default="python3")
    args = parser.parse_args()

    result = install_session_end_hook(
        settings_path=args.settings,
        hook_root=args.hook_root,
        python_bin=args.python_bin,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
