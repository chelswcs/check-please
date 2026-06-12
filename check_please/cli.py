"""CLI entrypoint for token receipt."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .data import available_fields_report, estimate_cost, resolve_snapshot
from .html_render import render_receipt_html
from .models import ALLOWED_WIDTHS, DEFAULT_FOOTER, DEFAULT_PRICING, SUPPORTED_LANGUAGES
from .render import auto_brand, print_receipt, render_receipt

DEFAULT_CHAT_HTML_PATH = Path("/tmp/check-please.html")


def format_chat_reply(receipt_text: str, html_path: Optional[Path] = None) -> str:
    reply = f"```text\n{receipt_text}\n```"
    if html_path:
        reply += f"\n\nPrintable HTML: `{html_path.resolve()}`"
    return reply


def open_in_default_browser(path: Path) -> bool:
    result = subprocess.run(["open", str(path.resolve())], check=False)
    return result.returncode == 0


def parse_cli_language(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"en", "english"}:
        return "en"
    if normalized in {"zh", "zh-tw", "zh_tw", "tw", "繁體", "繁中", "traditional"}:
        return "zh-TW"
    if normalized in {"cantonese", "cantonese-hant", "cantonese_hant", "廣東話"}:
        return "cantonese"
    raise argparse.ArgumentTypeError("expected one of: en, zh, zh-TW, cantonese")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render token usage as an ASCII thermal receipt.")
    parser.add_argument("--session", type=Path, help="Codex JSONL session path. Defaults to newest local session.")
    parser.add_argument("--scope", choices=("latest-turn", "session", "today"), default="latest-turn", help="latest-turn or session bills one conversation; today aggregates every session of the current local day, broken down by model.")
    parser.add_argument("--width", type=int, choices=ALLOWED_WIDTHS, default=48)
    parser.add_argument("--agent-tool", choices=("auto", "codex", "claude-code", "opencode", "cursor", "manus", "antigravity", "trae", "generic"), default=None, help="Software data source and receipt logo. claude-code/codex/opencode read local logs; cursor/manus/antigravity/trae brand the receipt and expect manual token flags. When omitted, check-please uses the current runtime if it can detect one.")
    parser.add_argument("--brand", choices=("auto", "codex", "claude-code", "opencode", "cursor", "manus", "antigravity", "trae", "generic"), default=None, help="Backward-compatible logo override. Prefer --agent-tool when choosing a software data source.")
    parser.add_argument(
        "--opencode-session-id",
        default=None,
        help="OpenCode session id (ses_…) when reading an opencode*.db SQLite file via --session, or together with --agent-tool opencode.",
    )
    parser.add_argument(
        "--language",
        "--lang",
        dest="language",
        type=parse_cli_language,
        choices=SUPPORTED_LANGUAGES,
        default="en",
        metavar="{en,zh,zh-TW,cantonese}",
        help="Receipt language: en, zh-TW, or cantonese. The short alias zh resolves to zh-TW, not Simplified Chinese.",
    )
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING)
    parser.add_argument("--footer", default=DEFAULT_FOOTER, help="Custom footer line, or 'auto' for model-aware footer.")
    parser.add_argument("--footer-tone", choices=("auto", "snarky", "encouraging", "dry"), default="auto")
    parser.add_argument("--conversation-hint", default="", help="Optional short hint used to vary auto footer selection.")
    parser.add_argument("--conversation-summary", default="", help="Alias for a current-chat summary used to vary auto footer selection.")
    parser.add_argument("--provider", help="Override provider, e.g. openai or anthropic.")
    parser.add_argument("--model", help="Override model for display and pricing.")
    parser.add_argument("--input-tokens", type=int)
    parser.add_argument("--cached-input-tokens", type=int)
    parser.add_argument("--cache-write-tokens", type=int)
    parser.add_argument("--output-tokens", type=int)
    parser.add_argument("--reasoning-output-tokens", type=int)
    parser.add_argument("--total-tokens", type=int)
    parser.add_argument("--context-window", type=int)
    parser.add_argument("--receipt-seed")
    parser.add_argument("--show-fields", action="store_true", help="Print a JSON report of fields available from the selected source instead of a receipt.")
    parser.add_argument("--output", choices=("text", "html"), default="text", help="Receipt output format. Use html for a printable browser page.")
    parser.add_argument("--write", type=Path, help="Write the rendered receipt to a file and suppress stdout. Useful when a host tool would otherwise echo the receipt multiple times.")
    parser.add_argument("--write-html", type=Path, help="Also write a printable HTML receipt to a file while keeping the main output unchanged.")
    parser.add_argument("--open-html", action="store_true", help="Open the generated HTML receipt in the system default browser after writing it.")
    parser.add_argument("--chat-reply", action="store_true", help="Print a chat-ready reply: fenced receipt text plus a Printable HTML browser URL. When no --write-html path is given, /tmp/check-please.html is used automatically.")
    parser.add_argument("--stream", action="store_true", default=None, help="Print receipt one line at a time, like a receipt printer.")
    parser.add_argument("--no-stream", dest="stream", action="store_false", help="Print receipt all at once even in an interactive terminal.")
    parser.add_argument("--stream-delay", type=float, default=0.03, help="Delay in seconds between lines when --stream is used.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    snapshot = resolve_snapshot(args)
    if args.provider:
        snapshot.provider = args.provider
    if args.model:
        snapshot.model = args.model

    if args.show_fields:
        fields_json = json.dumps(available_fields_report(snapshot), indent=2, ensure_ascii=True)
        if args.write:
            args.write.parent.mkdir(parents=True, exist_ok=True)
            args.write.write_text(fields_json + "\n", encoding="utf-8")
            return 0
        print(fields_json)
        return 0

    estimate = estimate_cost(snapshot, args.pricing)
    agent_tool = auto_brand(snapshot.provider, snapshot.source, args.agent_tool or args.brand or "auto")
    conversation_hint = args.conversation_summary or args.conversation_hint
    language = args.language
    html_target = args.write_html
    if args.chat_reply and html_target is None and args.output != "html":
        html_target = DEFAULT_CHAT_HTML_PATH
    html_receipt = None
    if args.output == "html" or html_target:
        html_receipt = render_receipt_html(snapshot, estimate, args.width, agent_tool, args.footer, args.footer_tone, conversation_hint, language)
    if args.output == "html":
        receipt_text = html_receipt or render_receipt_html(snapshot, estimate, args.width, agent_tool, args.footer, args.footer_tone, conversation_hint, language)
    else:
        receipt_text = render_receipt(snapshot, estimate, args.width, agent_tool, args.footer, args.footer_tone, conversation_hint, language)
    if html_target:
        html_target.parent.mkdir(parents=True, exist_ok=True)
        html_target.write_text((html_receipt or "") + "\n", encoding="utf-8")
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(receipt_text + "\n", encoding="utf-8")
    if html_target and args.open_html:
        open_in_default_browser(html_target)
    if args.chat_reply:
        print(format_chat_reply(receipt_text, html_target))
        return 0
    if args.write:
        return 0
    if args.output == "html":
        print(receipt_text)
        return 0
    stream = sys.stdout.isatty() if args.stream is None else args.stream
    print_receipt(receipt_text, stream, args.stream_delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
