<div align="center">
  <p>
    <a href="./README.md">English</a> |
    <a href="./README.zh-TW.md">繁體中文</a> |
    <a href="./README.cantonese.md">廣東話</a>
  </p>
  <h1>check-please</h1>
  <p><strong>把 AI Token 用量變成一張有梗的收據。</strong></p>
</div>

## 這是什麼

`check-please` 會把 AI Token 用量變成一張 monospace 熱感紙收據，可以貼進對話、列印，或存成 PNG。

它先讀本機真實日誌，再用 `check_please/pricing.json` 的官方價格表估算成本；對應不到價格的模型會誠實顯示 `UNMAPPED`，不會編造數字。

## 預覽

```text
                    ▐▛███▜▌
                   ▝▜█████▛▘
                     ▘▘ ▝▝
                  CLAUDE CODE

                感謝使用 Claude
        收據號碼: CC_20260427_151928_7CE382
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
總計                               15,702 Tokens
────────────────────────────────────────────────
USD 預估                               $0.062851
價格對應                       claude-sonnet-4.5
價格日期                              2026-06-12
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              想太多也是要收費的

        ||| ||||| || ||| | | || |||  | |
           CC_20260427_151928_7CE382
```

## 安裝

建議用 Skills CLI 安裝：

```bash
npx skills add https://github.com/chelswcs/check-please -g -y
```

只想裝在特定工具：

```bash
npx skills add https://github.com/chelswcs/check-please -a claude-code -y
npx skills add https://github.com/chelswcs/check-please -a codex -y
npx skills add https://github.com/chelswcs/check-please -a opencode -y
```

本機 CLI 使用：

```bash
python3 -m pip install -e .
check-please --agent-tool claude-code --chat-reply
```

## 怎麼用

在對話裡說下面任何一句，或直接執行 CLI：

- `check please` / `token receipt`
- `埋單` / `結帳` / `發票` / `打單`
- `token 收據` / `AI 用量帳單` / `把這次對話打成收據`
- 全日帳單：`今日帳單` / `全日用量單` / `daily usage`

範例：

```bash
# 單一對話（文字收據 + 可列印 HTML 會用系統瀏覽器開啟）
python3 scripts/check_please.py --agent-tool claude-code --chat-reply

# 全日帳單：今天所有會話，每個模型一行
python3 scripts/check_please.py --agent-tool claude-code --scope today --chat-reply

# 語言：en | zh-TW | cantonese
python3 scripts/check_please.py --agent-tool claude-code --language zh-TW --chat-reply

# 直接輸出 HTML 並在瀏覽器開啟
python3 scripts/check_please.py --agent-tool claude-code --write-html ./receipt.html --open-html
```

## HTML 預覽

HTML 收據是單一獨立檔案（樣式與功能全部內嵌，離線也能開啟），做成熱感印表機的樣子：

- 紙會從出紙口印出來，帶回彈，然後微微飄動、微彎；底部鋸齒撕邊是真實裁切，陰影跟著輪廓走。
- **Print receipt**：用列印樣式輸出乾淨的 80mm 收據。
- **Save PNG**：匯出 3× PNG（檔名用收據號碼），按下去會有撕紙動畫，然後印表機重新印一張。零外部依賴，離線可用。
- **EN / 繁中 / 廣東話** 切換會用所選語言重新印一次。
- 小費面板（15/18/20/25%）會加上「小計 / 小費 / 應付總額」。

## 全日帳單

`--scope today` 聚合當天本地時區內的所有會話：

- 每個模型一行、各自計價；不同貨幣分開出總額。
- 表頭不用工具 logo，改用「全日帳單」標題，摘要顯示會話數。
- 跨午夜的會話只計入時間戳落在今天的訊息（Codex 例外：其日誌為會話累計，按最後事件日期歸帳）。

## 自動出單（Claude Code）

會話結束時自動出收據。兩張單都可由使用者在 `~/.claude/check-please.json` 開關：

```bash
# 關閉會話時出該會話收據（預設開）+ 當日累計帳單（預設關）
python3 scripts/install_claude_auto_trigger.py --daily-receipt on
python3 scripts/uninstall_claude_auto_trigger.py
```

## 支援軟體

| 軟體 | 狀態 | 資料來源 | 備註 |
| --- | --- | --- | --- |
| Claude Code | `已支援` | `~/.claude/projects` transcripts | 逐訊息用量，含快取讀寫分項；`latest-turn` / `session` / `today` |
| Codex | `已支援` | Codex JSONL sessions | `token_count` 事件；`latest-turn` / `session` / `today` |
| OpenCode | `已支援` | `opencode*.db` SQLite | assistant 訊息的 tokens + `modelID`；全部 scope |
| Cursor / Manus / Antigravity / Trae / 其他 agent | `手動模式` | 無穩定本地用量日誌 | Agent 自行帶 `--input-tokens` / `--output-tokens`，配 `--agent-tool <host>` 顯示工具名稱 |

## 價格

`check_please/pricing.json` 是唯一價格來源，收錄 Anthropic / OpenAI / Google 官方價格（含已公開的快取價格）。其餘模型一律顯示 `UNMAPPED` —— 誠實優先。

---

<sub>靈感來自 [Hchen1218/token-receipt](https://github.com/Hchen1218/token-receipt) 與 [chrishutchinson/claude-receipts](https://github.com/chrishutchinson/claude-receipts)。</sub>
