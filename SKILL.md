---
name: check-please
description: Use when the user wants to view AI conversation token usage as a receipt, invoice, checkout slip, token bill, usage receipt, cost snapshot, daily usage bill, or creative monospace thermal-paper artifact. Trigger on "check please" and Chinese prompts like 埋單, 結帳, 發票, 打單, 查看本次對話 Token 消耗, 生成 token 收據, AI 用量帳單, 把這次對話打成收據, 看看這輪 token 消耗, 今日用咗幾多 token, 今日 token 帳單, 全日用量單, 今日使費, 繁體中文 token 收據, 廣東話 token 單, or any request to make token/context usage visually shareable.
---

# Check Please

Turn the token usage of an AI conversation into a monospace thermal-paper receipt that is worth screenshotting. Visual quality beats report completeness, but the numbers must stay honest: real local logs first, official pricing estimates second, and anything missing is labelled instead of invented.

## Triggering

Phrases that should trigger a **single-conversation receipt** directly:

- `check please`
- `埋單` / `結帳` / `發票` / `打單`
- `token receipt` / `token bill` / `usage receipt`
- `token 收據` / `對話發票` / `AI 用量帳單`
- `把這次對話打成收據` / `看看這輪 token 消耗` / `查看本次對話 Token 消耗`
- `繁體中文 token 收據` / `廣東話 token 單`

Phrases that should trigger the **whole-day bill** (`--scope today`, one line item per model):

- `今日用咗幾多 token` / `今日 token 帳單` / `今日用量單`
- `全日用量` / `成日用咗幾多` / `今日帳單`
- `daily usage` / `today's bill`

With the auto-trigger installed, Claude Code also prints receipts on `SessionEnd` (see Auto-trigger below). More phrase guidance: `references/trigger-phrases.md`.

## Quick start

```bash
python3 scripts/check_please.py --agent-tool claude-code --chat-reply
python3 scripts/check_please.py --agent-tool codex --chat-reply
python3 scripts/check_please.py --agent-tool opencode --chat-reply
```

`--chat-reply` does four things at once: prints the full receipt as the chat reply body, writes `/tmp/check-please.html`, opens that printable HTML file in the system default browser, and leaves a plain-text `Printable HTML: /tmp/check-please.html` fallback path. Prefer it over hand-rolling `--write` + `--write-html` two-step flows. Do not run a default pass first and a second pass after grepping logs — that just prints duplicate logos in the tool output.

Whole-day bill (aggregates every session of the current local day, one line item per model, totals kept per currency):

```bash
python3 scripts/check_please.py --agent-tool claude-code --scope today --chat-reply
```

Other useful flags:

```bash
python3 scripts/check_please.py --agent-tool codex --model gpt-5.4 --width 48 --stream
python3 scripts/check_please.py --provider anthropic --agent-tool claude-code --model claude-sonnet-4-5 --input-tokens 12487 --cached-input-tokens 8742 --output-tokens 3215
python3 scripts/check_please.py --footer-tone snarky --conversation-summary "one-line summary of this conversation"
python3 scripts/check_please.py --show-fields
python3 scripts/check_please.py --language cantonese   # en | zh-TW | cantonese
```

In an interactive terminal the receipt prints line by line; piped output prints as one block. Force with `--stream` / `--no-stream`. When replying in chat, wrap the receipt in a fenced code block to keep the monospace layout.

## Chat reply contract

- The default reply is the complete artifact: receipt fenced code block + a plain-text `Printable HTML: /tmp/check-please.html` fallback path. `--chat-reply` also opens it in the system default browser, but the chat body must not include a `file://` URI or Markdown link because Electron hosts may capture those links in-app.
- Never reply with only `RECEIPT # / TOTAL / USD ESTIMATE` style summaries; always show the full receipt body.
- Only deviate when generation fails, fields are too incomplete to print, or the user explicitly asks for an explanation — and even then, shortest note first, then the receipt or the error.

````text
```text
<full receipt here>
```

Printable HTML: /tmp/check-please.html
````

## Hosts and data sources

Two tiers. Never read another host's logs just because they are newer; if the runtime cannot be detected and multiple logs exist locally, require an explicit `--agent-tool` rather than guessing.

**Auto (local logs are read directly):**

| Host | Data source | Notes |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/**/*.jsonl` transcripts | Per-message `usage` (input, cache read, cache write, output) and `model`; `CLAUDE_SESSION_ID` picks the session, newest transcript otherwise. Receipt `Input Tokens` includes cache reads/writes. Zero-usage `<synthetic>` rows are skipped. |
| Codex | `~/.codex/sessions/**/*.jsonl` | `token_count` events: `last_token_usage` for `--scope latest-turn` (default), `total_token_usage` for `--scope session`. Model from `session_meta` then `turn_context`. |
| OpenCode | `opencode*.db` SQLite (`~/.local/share/opencode/`, `OPENCODE_DATA_DIR`, `%LOCALAPPDATA%\opencode`) | Assistant rows' `tokens.*` + `modelID`; `--opencode-session-id ses_...` or `OPENCODE_SESSION_ID`; latest-turn takes the last assistant row, session sums them. |

**Manual (host has no stable local usage log):** `cursor`, `manus`, `antigravity`, `trae`, and any other agent host. The agent running inside the host knows its own usage (host UI / API response usage fields) — pass it through manual flags and keep the host branding:

```bash
python3 scripts/check_please.py --agent-tool cursor --provider anthropic --model claude-sonnet-4-6 --input-tokens 12487 --output-tokens 3215 --chat-reply
```

Use `--agent-tool generic` when no host name fits.

## Scopes

- `latest-turn` (default): the most recent turn.
- `session`: the whole conversation.
- `today`: every session of the current local day, aggregated per model. Cross-midnight sessions only count messages whose timestamp falls on today (Codex is the exception: its logs are session-cumulative, attributed by last-event date). Cannot be combined with `--session`.

Daily receipts differ visually: the host logo is replaced with a `DAILY TOTAL` masthead (`全日帳單` / `全日埋單`), the summary shows a session count instead of context, line items are one row per model, and pricing lists each model's cost followed by one total per currency (currencies are never mixed into one number).

## Auto-trigger (Claude Code SessionEnd)

Two receipts, each user-toggleable via `~/.claude/check-please.json`:

- `session_receipt` (default on): receipt for the session being closed.
- `daily_receipt` (default off): appends the running whole-day bill; the last close of the day shows the final daily total.

```bash
python3 scripts/install_claude_auto_trigger.py --daily-receipt on
python3 scripts/install_claude_auto_trigger.py --session-receipt off --daily-receipt on
python3 scripts/uninstall_claude_auto_trigger.py
```

For a fixed-time daily bill instead, use cron:

```
55 23 * * * python3 /path/to/check-please/scripts/check_please.py --agent-tool claude-code --scope today --write-html ~/check-please-daily.html
```

Only install auto-trigger on hosts verified to support a `SessionEnd`-style hook; do not assume other hosts have one.

## Pricing

- `check_please/pricing.json` is the only pricing source. It currently covers official Anthropic / OpenAI / Google rates (including cache read/write where published).
- Unknown models show `PRICE: UNMAPPED` — never invent or approximate an amount.
- Each entry keeps its own currency; USD models show `USD ESTIMATE`, CNY models would show `CNY ESTIMATE`, and multi-currency daily bills print one total per currency.

## HTML preview

`--chat-reply` / `--output html` / `--write-html` produce a self-contained page (no external JS):

- Thermal-printer intro animation: the paper feeds out of the slot with a bounce, then hangs with a gentle sway and curl shading; torn zigzag bottom edge is a real cutout with a silhouette-following shadow.
- Topbar: `Print receipt` (print stylesheet outputs a clean 80mm receipt), `Save PNG` (dependency-free 3× PNG export named after the receipt id, with a tear-off animation and automatic reprint), and an `EN / 繁中 / 廣東話` switch that re-prints the receipt in the chosen language.
- Tip panel (15/18/20/25%) below the paper adds `SUBTOTAL / TIP / GRAND TOTAL` rows and swaps the footer line; it only appears when the receipt has a priced estimate.
- Honors `prefers-reduced-motion`.

## Visual rules

- Width 48 by default (42/48/56/64 allowed); every line must fit the width.
- Host logos: Codex, Claude Code (pixel crab), Trae, OpenCode pixel blocks; Cursor / Manus / Antigravity get text label bands; unknown hosts get `AI CHECKOUT`. The thanks line follows the model/provider (Claude, ChatGPT, Gemini…), never the host logo.
- Stable line items: `Input Tokens`, `Output Tokens`, `Cache Read Tokens`, `TOTAL`. Optional when present: `Reasoning Tokens`, `Cache Write Tokens`. Never print unconfirmed fields (`System Tokens`, `Tool Use Tokens`).
- `CONTEXT USED` replaces any scope label; shows `used/window` when a context window is known.
- Footer lines come from `check_please/footer_copy.json` (including tip tiers `tip_15/tip_20/tip_25`), picked deterministically per conversation; pass `--conversation-summary` to vary it, or `--footer` to override. Max 2 lines.
- Layout details: `references/receipt-style.md`. Field availability: `references/available-fields.md`.

## Architecture

- `check_please/cli.py` — thin CLI entry (`scripts/check_please.py` wraps it).
- `check_please/data.py` — log readers (Claude transcripts, Codex JSONL, OpenCode SQLite), daily aggregation, pricing lookup, `--show-fields` report.
- `check_please/models.py` — snapshot/estimate dataclasses, width-aware text helpers.
- `check_please/render.py` — receipt view model, text renderer, logos, footer selection, barcode.
- `check_please/html_render.py` — printable HTML page (animation, PNG export, languages, tips).
- `check_please/hooks.py` — SessionEnd hook payload, receipt config, install/uninstall.
- `check_please/pricing.json` / `check_please/footer_copy.json` — single sources for rates and footer copy.

## Validation

After any change, run:

```bash
python3 scripts/validate_receipt.py
```

It checks line widths, required fields, logo alignment, barcode, HTML structure (printer, PNG export, language switch), pricing fallbacks, daily aggregation, and the SessionEnd hook end to end.
