# Check Please 触发词

目标不是只有在用户说出 `receipt` 时才触发，而是把“想看这次对话 token / context / 成本小票”的表达都稳稳接住。

## 强触发

这些说法默认应该直接调用 `check-please`：

- `token receipt`
- `token 小票`
- `对话发票`
- `AI 用量账单`
- `token bill`
- `usage receipt`
- `cost receipt`
- `print token receipt`
- `把这次对话打成小票`
- `看看这轮 token 消耗`
- `生成本次对话 token 小票`
- `查看本次对话 Token 消耗`
- `繁體中文 token 小票`
- `廣東話 token 小票`
- `廣東話 token receipt`

## 弱触发

这些说法如果上下文明显是在要“可展示的小票”，也应该触发：

- `context 用了多少`
- `这轮花了多少钱`
- `把 token 消耗打印出来`
- `给我一张 token checkout`
- `本次对话成本`
- `这次上下文用了多少`
- `把这次 AI 用量做成发票`
- `用繁體中文出小票`
- `用廣東話出小票`

## Claude Code 自动触发

Claude Code 的 `SessionEnd` auto-trigger 不依赖触发词；会话结束后自动出票。

但在会话中途，下面这些词仍然应触发手动出票：

- `token receipt`
- `receipt`
- `token 小票`
- `对话发票`
- `AI 用量账单`

## 避免误触发

下面这些情况不要直接触发：

- 用户只是在讨论 `pricing strategy`，没有要当前对话账单
- 用户只是在泛谈 `token` 或 `context window`
- 用户要的是表格、CSV、统计分析，而不是小票形式
