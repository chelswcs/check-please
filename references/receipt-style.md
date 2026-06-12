# Check Please 視覺規範

目標唔係做「準確但無聊嘅表格」，而係做一張可以截圖分享嘅熱感紙收據。單面要穩定適配 monospace；Logo 區允許用 `█░▒▓▐▛▜▌▘▝` 做像素塊，金額區允許 `¥` 表示人民幣，其餘內容盡量保持 ASCII。

## 單面結構

1. 頂部品牌區：像素感頭圖 + 產品名（全日單改用「全日埋單」masthead）。
2. 說明區：`THANK YOU FOR CODING WITH ...`、receipt id、日期、provider、model、context used。
3. 明細區：`ITEM / TOKENS` 兩欄，數字靠右對齊。
4. 總計區：`TOTAL` 單獨加重，唔好埋喺明細入面。
5. 金額區：官方估算金額，按模型條目顯示 `USD ESTIMATE` 或 `CNY ESTIMATE`；對應唔到價格時顯示 `PRICE: UNMAPPED`。
6. 底部分享區：一句根據模型同當前對話總結生成嘅短 footer + ASCII 條碼 + receipt id。

## 預設闊度

預設 48 字元；可選 42、48、56、64。腳本必須保證每一行唔超過指定闊度。

## 品牌頭圖方向

頂部 logo 按 Agent 工具決定，唔按模型決定。感謝語按模型決定，唔按 Agent 工具決定。

Codex：

```text
                  █████
                █    ██   ███
              ███ ██    ██   █
            ██ ██ ██████   ███
            █  ██ ██    ███   █
            ██   ███    █  ██  █
              ███   █████  ██ ██
              █   ██    █  ███
               ███   ██    █
                     █████
                      CODEX
```

Claude Code：

```text
                    ▐▛███▜▌
                   ▝▜█████▛▘
                     ▘▘ ▝▝
                  CLAUDE CODE
```

Trae：

```text
                 ██████████████
              ███▒▒▒▒▒▒▒▒▒▒▒▒▒▒███
              ███▒▒██████████▒▒███
              ███▒▒██▒▒▒█▒▒▒█▒▒███
              ███▒▒██████████▒▒███
              █████▒▒▒▒▒▒▒▒▒▒▒▒███
                 █████████████
                       TRAE
```

Generic：

```text
          [ AI CHECKOUT ]
```

## 文案原則

- 單面欄位保留收據感但提高可讀性。通用穩定欄位固定為：`Input Tokens`、`Output Tokens`、`Cache Read Tokens`、`TOTAL`。
- 分隔線要分強弱兩級：粗主分隔線用嚟切主區域，細副分隔線用嚟承接表頭同次區塊，唔好成張單只用一種橫線。
- 可選欄位固定為：`Reasoning Tokens`、`Cache Write Tokens`。有真實欄位就顯示，冇就略過。
- 唔好輸出來源不確定嘅欄位。例如 `System Tokens`、`Tool Use Tokens` 唔入單面。
- 多貨幣價格必須保留來源口徑，唔同貨幣分開出總額，唔好夾埋加。
- 感謝語入面嘅模型/品牌名保留標準寫法，例如 `ChatGPT`、`Gemini`，唔好全部壓成 `CHATGPT`。
- 條碼使用原版 `|` 細直線組合，保持輕量嘅 ASCII 收據質感。
- 目前版本唔做 QR code；對話收據同預設單面繼續保留條碼 + receipt id 結構。
- 互動式終端入面預設逐行輸出 receipt；如果輸出被 pipe 或腳本捕獲，就預設整塊輸出。需要強制逐行用 `--stream`，需要強制整塊用 `--no-stream`。聊天回覆仍然用代碼區塊保持等闊排版。
- 解釋性中文唔好放入單面，放喺 Skill 回覆正文入面。
- footer 要短、有記憶點，而且要似「呢次對話自己嘅句子」。實現上句庫來自 `footer_copy.json`（對齊文案表），按對話摘要等種子穩定揀句。
- 黑色幽默要可讀，似模型輕輕吐槽用戶，而唔係文案模板套詞。優先接近呢類感覺：`REASONING WAS BILLED SEPARATELY.`、`THE LAST REVISION WAS NOT THE LAST.`、`THE PRICE TAG IS HONEST. THE PROCESS WAS NOT.`；唔好生成前言不對後語嘅句子。
- 預設語氣限制喺黑色幽默或者暖心鼓勵之間；顯式 `--footer-tone` 仍然可以強制風格。
- footer 最多 2 行，每行控制喺緊湊長度內，避免把收據下半區迫爆。
