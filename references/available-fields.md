# Check Please 可讀欄位口徑

呢個 Skill 嘅預設數據源係本地日誌（Claude transcripts / Codex session JSONL / OpenCode SQLite），唔係模型自己估出嚟嘅數字。運行：

```bash
python3 scripts/check_please.py --show-fields
```

可以查看目前選中 session 或手動參數入面真實可用嘅欄位。

## Codex JSONL 目前讀到

來自 `event_msg.payload.type == "token_count"` 嘅 `info.last_token_usage` 或 `info.total_token_usage`：

- `input_tokens`
- `cached_input_tokens`
- `output_tokens`
- `reasoning_output_tokens`
- `total_tokens`

來自同一個 `token_count.info`：

- `model_context_window`

來自 `session_meta.payload`、`turn_context.payload` 或調用參數：

- `model_provider`
- `id`
- `timestamp`
- `model` / `model_id` / `model_name` / `model_slug`
- `turn_context.model`：當 `session_meta` 冇寫模型時，Codex 日誌通常仲可以由呢度補到當前回合嘅模型

模型讀取順序係：`session_meta.model*` -> `turn_context.model` -> 調用參數 `--model`。前兩者都冇時，收據先顯示 `MODEL: UNRECORDED`。

## Claude transcripts（`~/.claude/projects`）目前讀到

每條 assistant 訊息嘅 `message.usage`：

- `input_tokens`（未命中 cache 嘅輸入）
- `cache_read_input_tokens`
- `cache_creation_input_tokens`
- `output_tokens`

連同 `message.model`、`sessionId`、`timestamp`。收據口徑入面 `Input Tokens` 會包埋 cache read/write。

## 預設單面固定欄位

為咗令各 Agent 工具都可以穩定支援，預設通用條目固定為：

- `Input Tokens` <- `input_tokens`
- `Output Tokens` <- `output_tokens`
- `Cache Read Tokens` <- `cached_input_tokens`
- `TOTAL` <- `total_tokens`

呢啲條目只有欄位真實存在時先輸出；`TOTAL` 用日誌入面嘅 `total_tokens`，手動模式會由 input + output 補底計算。

## 可選欄位

以下欄位已經固定為可選條目：有真實欄位就顯示，冇就略過。

- `Reasoning Tokens` <- `reasoning_output_tokens`
- `Cache Write Tokens` <- `cache_write_tokens` 或 Anthropic 嘅 `cache_creation_input_tokens`

## 唔輸出

- `System Tokens`：目前 Codex `token_count` 事件冇獨立欄位。
- `Tool Use Tokens`：目前 Codex `token_count` 事件冇獨立欄位。

原則：真實可讀欄位優先；不可讀欄位唔寫；可選欄位有就顯示，冇就略過。
