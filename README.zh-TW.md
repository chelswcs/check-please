<div align="center">
  <p>
    <a href="./README.md">English</a> |
    <a href="./README.zh-TW.md">繁體中文</a> |
    <a href="./README.cantonese.md">Cantonese</a>
  </p>
  <h1>check-please</h1>
  <p><strong>把 AI 用量，印成一張自帶補刀的收據。</strong></p>
</div>

## 這是什麼

`check-please` 會把本次 AI 對話的 token / context 用量，整理成一張 monospace 熱敏紙收據。

它不是儀表板，也不是試算表。它優先讀本機真實日誌，再依照 `references/pricing.json` 的價格表估算成本；對不上價格時會明確顯示未映射，不會亂編金額。

## 繁體中文與 Cantonese

目前 CLI 支援三種語言：

```bash
python3 scripts/check_please.py --language en
python3 scripts/check_please.py --language zh-TW
python3 scripts/check_please.py --language cantonese
```

`--language zh` 是繁體中文捷徑，會被正規化成 `zh-TW`；這個專案不再輸出簡體中文版本。

HTML 版本也會同時產生 `EN / 繁中 / 廣東話` 切換，不需要重新輸出檔案。

## 安裝

建議用 Skills CLI 安裝：

```bash
npx skills add https://github.com/chelswcs/check-please -g -y
```

只想裝到特定工具也可以：

```bash
npx skills add https://github.com/chelswcs/check-please -a codex -y
npx skills add https://github.com/chelswcs/check-please -a claude-code -y
npx skills add https://github.com/chelswcs/check-please -a opencode -y
```

## 快速使用

主流程是 local-only：在聊天裡輸出收據，同時在本機寫出可列印 HTML，不需要部署網站。

```bash
python3 scripts/check_please.py --agent-tool codex --chat-reply --language zh-TW
python3 scripts/check_please.py --agent-tool claude-code --chat-reply --language zh-TW
python3 scripts/check_please.py --agent-tool kimi-code --chat-reply --language zh-TW
python3 scripts/check_please.py --agent-tool opencode --chat-reply --language zh-TW
```

手動資料範例：

```bash
python3 scripts/check_please.py \
  --provider anthropic \
  --agent-tool claude-code \
  --model claude-sonnet-4.5 \
  --input-tokens 12487 \
  --cached-input-tokens 8742 \
  --cache-write-tokens 1024 \
  --output-tokens 3215 \
  --language zh-TW
```

## 觸發語

- `token receipt`
- `token 收據`
- `AI 用量帳單`
- `把這次對話打成收據`
- `查看本次對話 Token 消耗`
- `繁體中文 token 收據`
- `用繁體中文出收據`

## 可列印 HTML

建議使用 `--chat-reply`。它會輸出聊天用收據，並自動寫出本機檔案 `/tmp/check-please.html`。

```bash
python3 scripts/check_please.py --agent-tool codex --chat-reply --language zh-TW
```

也可以只輸出 HTML：

```bash
python3 scripts/check_please.py --agent-tool claude-code --output html --write ./receipt.html --language zh-TW
```

打開 `receipt.html` 後可以直接列印。若使用 `--chat-reply`，工具會自動寫出 `/tmp/check-please.html` 並在回覆底部附上連結。

## 分享連結

分享連結是 optional，不是 local-only launch 的必要功能。

單張收據可以輸出 zero-storage 分享連結：payload 只放在 URL 的 `#` 後面，server 收不到內容。

```bash
python3 scripts/check_please.py --agent-tool codex --output share-url --share-base https://your-site.example --language zh-TW
```

schema 寫在 `references/share-payload.md`。如果只需要本機 HTML，就不用設定 domain 或部署網站。

## 修改文案

繁體中文與廣東話的 footer 句庫放在 `check_please/footer_copy.json`。

想調語氣時，直接改 `zh-TW` 或 `cantonese` 底下的 `snarky`、`dry`、`encouraging` 分組；程式會依照本次對話主題選用 `visual`、`pricing`、`debug`、`shipping`、`iteration`、`reasoning`、`context` 或 `default`。

## 驗證

修改後請至少跑：

```bash
python3 scripts/validate_receipt.py
```
