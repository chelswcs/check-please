<div align="center">
  <p>
    <a href="./README.md">English</a> |
    <a href="./README.zh-TW.md">繁體中文</a> |
    <a href="./README.cantonese.md">Cantonese</a>
  </p>
  <h1>check-please</h1>
  <p><strong>Turn AI token usage into a receipt with a punchline.</strong></p>
</div>

## What It Is

`check-please` turns AI token usage into a monospace thermal-paper receipt you can paste into chat, print, or save as a PNG.

It reads local logs first, estimates cost from the official pricing table in `check_please/pricing.json` second, and keeps missing data honest — unknown models show `UNMAPPED` instead of an invented number.

## Preview

```text
                    ▐▛███▜▌
                   ▝▜█████▛▘
                     ▘▘ ▝▝
                  CLAUDE CODE

        THANK YOU FOR CODING WITH Claude
      RECEIPT #: CC_20260427_151928_7CE382
           DATE: 2026-04-27 15:19:28
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROVIDER                               ANTHROPIC
MODEL                          claude-sonnet-4.5
CONTEXT USED                              12,487
────────────────────────────────────────────────
ITEM                                      TOKENS
────────────────────────────────────────────────
Input Tokens                              12,487
Output Tokens                              3,215
Cache Read Tokens                          8,742
Reasoning Tokens                             128
Cache Write Tokens                         1,024
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                              15,702 TOKENS
────────────────────────────────────────────────
USD ESTIMATE                           $0.062851
PRICE                          claude-sonnet-4.5
PRICE DATE                            2026-06-12
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    THE LOGO LOOKS CALM. THE BILL DOES NOT.

        ||| ||||| || ||| | | || |||  | |
           CC_20260427_151928_7CE382
```

## Install

Recommended: install it with the Skills CLI.

```bash
npx skills add https://github.com/chelswcs/check-please -g -y
```

If you only want it in a specific host, install it there:

```bash
npx skills add https://github.com/chelswcs/check-please -a claude-code -y
npx skills add https://github.com/chelswcs/check-please -a codex -y
npx skills add https://github.com/chelswcs/check-please -a opencode -y
```

For local CLI use:

```bash
python3 -m pip install -e .
check-please --agent-tool claude-code --chat-reply
```

## Use It

Say one of these in chat, or run the CLI directly:

- `check please` / `token receipt` / `usage receipt`
- `埋單` / `結帳` / `發票` / `打單`
- `token 收據` / `AI 用量帳單` / `把這次對話打成收據`
- Daily bill: `daily usage` / `today's bill` / `今日用咗幾多 token` / `全日用量單`

Examples:

```bash
# Single conversation (text receipt + printable HTML opened in your system browser)
python3 scripts/check_please.py --agent-tool claude-code --chat-reply

# Whole-day bill: every session today, one line item per model
python3 scripts/check_please.py --agent-tool claude-code --scope today --chat-reply

# Languages: en | zh-TW | cantonese
python3 scripts/check_please.py --agent-tool claude-code --language cantonese --chat-reply

# Printable HTML straight to the browser
python3 scripts/check_please.py --agent-tool claude-code --write-html ./receipt.html --open-html
```

## HTML Preview

The HTML receipt is a self-contained page styled like a thermal printer:

- The paper feeds out of the printer slot with a bounce, then hangs with a gentle sway and a slight curl; the torn zigzag bottom edge is a real cutout with a matching shadow.
- **Print receipt** outputs a clean 80mm receipt via the print stylesheet.
- **Save PNG** exports a 3× PNG named after the receipt id — complete with a tear-off animation before the printer reprints a fresh copy. No external libraries; works offline.
- **EN / 繁中 / 廣東話** switch re-prints the receipt in the chosen language.
- An optional tip panel (15/18/20/25%) adds `SUBTOTAL / TIP / GRAND TOTAL` rows.

## Daily Bill

`--scope today` aggregates every session of the current local day:

- One line item per model, priced individually; totals are kept per currency.
- The host logo is replaced by a `DAILY TOTAL` masthead, and the summary shows the session count.
- Cross-midnight sessions only count messages stamped today (Codex logs are session-cumulative and attributed by last-event date).

## Auto-trigger (Claude Code)

Print receipts automatically when a session ends. Both receipts are user-toggleable via `~/.claude/check-please.json`:

```bash
# session receipt on close (default on) + running daily bill (default off)
python3 scripts/install_claude_auto_trigger.py --daily-receipt on
python3 scripts/uninstall_claude_auto_trigger.py
```

## Supported Software

| Software | Status | Data source | Notes |
| --- | --- | --- | --- |
| Claude Code | `supported now` | `~/.claude/projects` transcripts | Per-message usage incl. cache read/write splits; `latest-turn` / `session` / `today` |
| Codex | `supported now` | Codex JSONL sessions | `token_count` events; `latest-turn` / `session` / `today` |
| OpenCode | `supported now` | `opencode*.db` SQLite (`~/.local/share/opencode/`, `OPENCODE_DATA_DIR`) | Assistant rows' tokens + `modelID`; all scopes |
| Cursor / Manus / Antigravity / Trae / other agents | `manual mode` | No stable local usage log | The agent passes its own usage via `--input-tokens` / `--output-tokens` with `--agent-tool <host>` for branding |

## Pricing

`check_please/pricing.json` is the single pricing source, covering official Anthropic / OpenAI / Google rates (including cache pricing where published). Anything else renders as `UNMAPPED` — honesty over guesswork.

---

<sub>Inspired by [Hchen1218/token-receipt](https://github.com/Hchen1218/token-receipt) and [chrishutchinson/claude-receipts](https://github.com/chrishutchinson/claude-receipts).</sub>
