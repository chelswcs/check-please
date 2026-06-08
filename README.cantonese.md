<div align="center">
  <p>
    <a href="./README.md">English</a> |
    <a href="./README.zh-TW.md">繁體中文</a> |
    <a href="./README.cantonese.md">Cantonese</a>
  </p>
  <h1>check-please</h1>
  <p><strong>將 AI 用量，印成一張識得補刀嘅單。</strong></p>
</div>

## 呢個係咩

`check-please` 會將今次 AI 對話用咗幾多 token / context，打成一張 monospace 熱敏紙單。

佢唔係 dashboard，亦唔係 spreadsheet。佢會先讀本機真實日誌，再用 `references/pricing.json` 入面嘅價格表估算成本；如果模型未對應到價格，就會老老實實顯示未對應，唔會扮識計。

## Cantonese / 廣東話版本

CLI 支援三種語言：

```bash
python3 scripts/check_please.py --language en
python3 scripts/check_please.py --language zh-TW
python3 scripts/check_please.py --language cantonese
```

`--language zh` 係繁體中文捷徑，會正規化成 `zh-TW`；呢個專案唔再輸出簡體中文版本。

HTML 版都會有 `EN / 繁中 / 廣東話` 切換，一份檔案就可以轉語言。

## 快速用法

主流程係 local-only：喺 chat 入面輸出單，同時喺本機寫出可打印 HTML，唔需要 deploy 網站。

```bash
python3 scripts/check_please.py --agent-tool codex --chat-reply --language cantonese
python3 scripts/check_please.py --agent-tool claude-code --chat-reply --language cantonese
python3 scripts/check_please.py --agent-tool kimi-code --chat-reply --language cantonese
python3 scripts/check_please.py --agent-tool opencode --chat-reply --language cantonese
```

手動資料例子：

```bash
python3 scripts/check_please.py \
  --provider anthropic \
  --agent-tool claude-code \
  --model claude-sonnet-4.5 \
  --input-tokens 12487 \
  --cached-input-tokens 8742 \
  --cache-write-tokens 1024 \
  --output-tokens 3215 \
  --language cantonese
```

## 觸發語

- `token receipt`
- `token 單`
- `token 小票`
- `AI 用量帳單`
- `把今次對話打成單`
- `把今次對話打成小票`
- `睇下今輪 token 消耗`
- `廣東話 token 單`
- `廣東話 token 小票`
- `用廣東話出單`
- `用廣東話出小票`
- `廣東話 token receipt`

## 可打印 HTML

建議用 `--chat-reply`。佢會輸出 chat 用單，並自動寫出本機檔案 `/tmp/check-please.html`。

```bash
python3 scripts/check_please.py --agent-tool codex --chat-reply --language cantonese
```

亦可以只輸出 HTML：

```bash
python3 scripts/check_please.py --agent-tool claude-code --output html --write ./receipt.html --language cantonese
```

開 `receipt.html` 就可以直接打印。用 `--chat-reply` 嘅話，工具會自動寫出 `/tmp/check-please.html`，再喺回覆底部加返條連結。

## 改文案

繁中同廣東話 footer 句庫放喺 `check_please/footer_copy.json`。

想再改語氣，就直接改 `zh-TW` 或 `cantonese` 入面嘅 `snarky`、`dry`、`encouraging` 分組；程式會跟今次對話主題揀 `visual`、`pricing`、`debug`、`shipping`、`iteration`、`reasoning`、`context` 或 `default`。

## 驗證

改完最少跑：

```bash
python3 scripts/validate_receipt.py
```
