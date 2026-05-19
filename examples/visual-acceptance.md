# Check Please 视觉验收

人工验收时先看视觉，不要先看字段清单。

## 必须通过

- 一眼像热敏纸小票，而不是普通表格。
- 在聊天里调用时，默认回复应该直接是完整 receipt 本体，而不是“已处理”“已打印”或字段摘要。
- 顶部有品牌感，能区分 Codex / Claude Code / Generic。
- Claude Code 顶部使用缩小版 `█` block 像素螃蟹轮廓，整块左边缘和主体不能歪。
- 顶部 logo 按 Agent 工具决定；感谢语按实际模型决定。
- `TOTAL` 是视觉中心。
- 底部有根据模型/当前对话总结变化的 footer 和条形码，适合截图传播。
- 终端运行时可以用 `--stream` 形成一行一行打印的小票效果。
- 所有价格都有来源口径；未知价格明确标注 `UNMAPPED`。
- 美元模型显示 `USD ESTIMATE`，人民币模型显示 `CNY ESTIMATE`；有平台或区域口径时显示 `RATE NOTE`。
- Token 明细只包含已固定且有来源的字段：通用字段 `Input Tokens`、`Output Tokens`、`Cache Read Tokens`、`TOTAL`；可选字段 `Reasoning Tokens`、`Cache Write Tokens` 有就显示。

## 应该拒绝

- Markdown 表格。
- 纯 JSON / YAML / CSV。
- 只有 token 数字，没有小票形态。
- 聊天回复里先写一段解释，再贴小票，导致视觉被打断。
- 只返回 `RECEIPT #`、`TOTAL`、`USD ESTIMATE` 这类摘录，而不是完整小票。
- 超宽换行导致截图不好看。
- 模型价格不匹配时硬算美元。
- 打印 `System Tokens`、`Tool Use Tokens` 或其他尚未固定的数据项。
- 出现 `DATA: SNAPSHOT`。
