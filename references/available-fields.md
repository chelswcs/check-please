# Check Please 可读字段口径

这个 Skill 的默认数据源是 Codex 本地 session JSONL，不是模型自己猜出来的数字。运行：

```bash
python3 scripts/check_please.py --show-fields
```

可以查看当前选中 session 或手动参数里真实可用的字段。

## Codex JSONL 目前能读到

来自 `event_msg.payload.type == "token_count"` 的 `info.last_token_usage` 或 `info.total_token_usage`：

- `input_tokens`
- `cached_input_tokens`
- `output_tokens`
- `reasoning_output_tokens`
- `total_tokens`

来自同一个 `token_count.info`：

- `model_context_window`

来自 `session_meta.payload`、`turn_context.payload` 或调用参数：

- `model_provider`
- `id`
- `timestamp`
- `model` / `model_id` / `model_name` / `model_slug`
- `turn_context.model`，当 `session_meta` 没写模型时，Codex 日志里通常还能从这里补到当前回合模型

模型读取顺序是：`session_meta.model*` -> `turn_context.model` -> 调用参数 `--model`。前两者都没有时，小票才显示 `MODEL: UNRECORDED`。

## 默认票面固定字段

为了让 Claude Code / Codex / Trae 三种 Agent 工具都能稳定支持，默认通用条目固定为：

- `Input Tokens` <- `input_tokens`
- `Output Tokens` <- `output_tokens`
- `Cache Read Tokens` <- `cached_input_tokens`
- `TOTAL` <- `total_tokens`

这些条目只有字段真实存在时才打印；`TOTAL` 使用日志里的 `total_tokens`，手动模式中会由 input + output 兜底计算。

## 可选字段

以下字段已经固定为可选条目：有真实字段就显示，没有就省略。

- `Reasoning Tokens` <- `reasoning_output_tokens`
- `Cache Write Tokens` <- `cache_write_tokens` 或 Anthropic 的 `cache_creation_input_tokens`

## 不打印

- `System Tokens`：当前 Codex `token_count` 事件没有独立字段。
- `Tool Use Tokens`：当前 Codex `token_count` 事件没有独立字段。

原则：真实可读字段优先；不可读字段不写；可选字段有就显示，没有就省略。
