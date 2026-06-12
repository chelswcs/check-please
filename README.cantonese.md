<div align="center">
  <p>
    <a href="./README.md">English</a> |
    <a href="./README.zh-TW.md">繁體中文</a> |
    <a href="./README.cantonese.md">Cantonese</a>
  </p>
  <h1>check-please</h1>
  <p><strong>將 AI 用量，印成一張識寸你嘅單。</strong></p>
</div>

## 呢個係咩

`check-please` 會將 AI Token 用量變成一張 monospace 熱感紙收據，可以貼入對話、列印，或者儲做 PNG。

佢唔係 dashboard，亦唔係 spreadsheet。佢會先讀本機真實日誌，再用 `check_please/pricing.json` 入面嘅官方價格表估算成本；如果模型對應唔到價格，就會老老實實顯示 `UNMAPPED`，唔會扮識計。

## 預覽

```text
                    ▐▛███▜▌
                   ▝▜█████▛▘
                     ▘▘ ▝▝
                  CLAUDE CODE

                多謝使用 Claude
        單號: CC_20260427_151928_7CE382
            日期: 2026-04-27 15:19:28
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
供應商                                 ANTHROPIC
模型                           claude-sonnet-4.5
已用上下文                                12,487
────────────────────────────────────────────────
項目                                       TOKEN
────────────────────────────────────────────────
輸入 Tokens                               12,487
輸出 Tokens                                3,215
快取讀取                                   8,742
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
總數                               15,702 Tokens
────────────────────────────────────────────────
USD 估算                               $0.062851
價格對應                       claude-sonnet-4.5
價格日期                              2026-06-12
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                諗得多好洗錢㗎

        ||| ||||| || ||| | | || |||  | |
           CC_20260427_151928_7CE382
```

## 安裝

建議用 Skills CLI 裝：

```bash
npx skills add https://github.com/chelswcs/check-please -g -y
```

只想裝喺某個工具入面：

```bash
npx skills add https://github.com/chelswcs/check-please -a claude-code -y
npx skills add https://github.com/chelswcs/check-please -a codex -y
npx skills add https://github.com/chelswcs/check-please -a opencode -y
```

本機 CLI 用法：

```bash
python3 -m pip install -e .
check-please --agent-tool claude-code --chat-reply --language cantonese
```

## 點用

喺對話入面講下面任何一句，或者直接行 CLI：

- `check please` / `token receipt`
- `埋單` / `結帳` / `發票` / `打單`
- `token 收據` / `AI 用量帳單` / `把今次對話打成收據`
- 全日單：`今日用咗幾多 token` / `全日用量單` / `成日用咗幾多`

例子：

```bash
# 單一對話（文字收據 + 可列印 HTML 一次出齊）
python3 scripts/check_please.py --agent-tool claude-code --chat-reply --language cantonese

# 全日埋單：今日所有會話，每個模型一行
python3 scripts/check_please.py --agent-tool claude-code --scope today --chat-reply --language cantonese

# 直接出 HTML 並喺瀏覽器打開
python3 scripts/check_please.py --agent-tool claude-code --write-html ./receipt.html --open-html
```

## HTML 預覽

HTML 收據係一個獨立檔案（樣式同功能全部內嵌，唔使連網都開到），整到似部熱感打印機：

- 張紙會由出紙口印出嚟，有回彈，之後微微飄動、微彎；底部鋸齒撕邊係真實裁切，個影跟住輪廓走。
- **Print receipt**：用列印樣式出一張乾淨嘅 80mm 收據。
- **Save PNG**：匯出 3× PNG（檔名用單號），撳落去仲有撕紙動畫，之後打印機重新印過一張。零外部依賴，離線都用到。
- **EN / 繁中 / 廣東話** 切換會用揀咗嘅語言重新印一次。
- 貼士面板（15/18/20/25%）會加埋「小計 / 貼士 / 埋單總數」。

## 全日埋單

`--scope today` 會聚合當日本地時區內所有會話：

- 每個模型一行、各自計價；唔同貨幣分開出總額。
- 表頭唔用工具 logo，改用「全日埋單」標題，摘要顯示傾咗幾多場。
- 跨午夜嘅會話只計時間戳落喺今日嘅訊息（Codex 例外：佢嘅日誌係會話累計，按最後事件日期歸帳）。

## 自動出單（Claude Code）

會話結束時自動出收據。兩張單都可以喺 `~/.claude/check-please.json` 自行開關：

```bash
# close session 出該會話收據（預設開）+ 當日累計埋單（預設關）
python3 scripts/install_claude_auto_trigger.py --daily-receipt on
python3 scripts/uninstall_claude_auto_trigger.py
```

## 支援軟件

| 軟件 | 狀態 | 數據來源 | 備註 |
| --- | --- | --- | --- |
| Claude Code | `已支援` | `~/.claude/projects` transcripts | 逐訊息用量，連快取讀寫分項；`latest-turn` / `session` / `today` |
| Codex | `已支援` | Codex JSONL sessions | `token_count` 事件；`latest-turn` / `session` / `today` |
| OpenCode | `已支援` | `opencode*.db` SQLite | assistant 訊息嘅 tokens + `modelID`；全部 scope |
| Cursor / Manus / Antigravity / Trae / 其他 agent | `手動模式` | 冇穩定本地用量日誌 | Agent 自己帶 `--input-tokens` / `--output-tokens`，配 `--agent-tool <host>` 顯示返個工具名 |

## 價格

`check_please/pricing.json` 係唯一價格來源，收錄 Anthropic / OpenAI / Google 官方價格（連已公開嘅快取價格）。其餘模型一律顯示 `UNMAPPED` —— 誠實行先。

---

<sub>靈感嚟自 [Hchen1218/token-receipt](https://github.com/Hchen1218/token-receipt) 同 [chrishutchinson/claude-receipts](https://github.com/chrishutchinson/claude-receipts)。</sub>
