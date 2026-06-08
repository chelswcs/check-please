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

`check-please` turns AI token usage into a monospace receipt you can paste into chat, print to HTML, or screenshot immediately.

It reads local logs first, estimates cost from official pricing data second, and keeps missing data honest instead of inventing it.

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
PRICE DATE                            2026-04-25
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
npx skills add https://github.com/chelswcs/check-please -a codex -y
npx skills add https://github.com/chelswcs/check-please -a claude-code -y
npx skills add https://github.com/chelswcs/check-please -a opencode -y
```

For local CLI use:

```bash
python3 -m pip install -e .
check-please --agent-tool codex --chat-reply
```

## Use It

Say one of these in chat, or run the CLI directly:

- `token receipt`
- `token bill`
- `usage receipt`
- `token 收據`
- `AI 用量帳單`
- `把這次對話打成收據`
- `看看這輪 token 消耗`
- `查看本次對話 Token 消耗`

Examples:

```bash
python3 scripts/check_please.py --agent-tool codex --chat-reply
python3 scripts/check_please.py --agent-tool claude-code --chat-reply
python3 scripts/check_please.py --agent-tool kimi-code --chat-reply
python3 scripts/check_please.py --agent-tool opencode --chat-reply
```

For a printable HTML file:

```bash
python3 scripts/check_please.py --agent-tool claude-code --output html --write ./receipt.html
```

## Supported Software

| Software | Status | Data source | Notes |
| --- | --- | --- | --- |
| Codex | `supported now` | Codex JSONL sessions | Reads local session logs directly |
| Claude Code | `supported now` | Claude usage-data + projects | Uses usage logs for tokens and transcripts for model lookup |
| Trae | `manual mode now` | Trae app storage | Auto transcript import is not shipped yet |
| Kimi Code | `supported now` | kimi-cli `context.jsonl` (`~/.kimi/sessions/` or `KIMI_SHARE_DIR`) | Reads cumulative `_usage.token_count`; USD estimate omitted (no API split); use manual flags if you need priced input/output |
| OpenCode | `supported now` | `opencode*.db` SQLite under `~/.local/share/opencode/` (see `OPENCODE_DATA_DIR`, `XDG_DATA_HOME`) | Reads `session`/`message` rows (`message.data` JSON: `tokens`, `modelID`); supports `--scope latest-turn` \| `session` |

## Notes

- Some Trae builds use `Trae CN` / `.trae-cn` instead of `Trae`.
- Inside Codex, the runtime can be detected and `check-please` reads Codex logs.
- Inside Claude Code's SessionEnd hook, `check-please` reads Claude Code usage logs.
- If you run the script from a plain shell and more than one local software log exists, pass `--agent-tool` explicitly.

## Footer

Inspired by [Hchen1218/token-receipt](https://github.com/Hchen1218/token-receipt) and [chrishutchinson/claude-receipts](https://github.com/chrishutchinson/claude-receipts).
