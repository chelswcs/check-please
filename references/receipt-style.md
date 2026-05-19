# Check Please 视觉规范

目标不是做“准确但无聊的表格”，而是做一张能截图传播的热敏纸小票。票面要稳定适配 monospace；Logo 区允许使用 `█░▒▓▐▛▜▌▘▝` 做像素块，金额区允许 `¥` 表示人民币，其余内容尽量保持 ASCII。

## 票面结构

1. 顶部品牌区：像素感头图 + 产品名。
2. 说明区：`THANK YOU FOR CODING WITH ...`、receipt id、日期、provider、model、context used。
3. 明细区：`ITEM / TOKENS` 两列，数字右对齐。
4. 总计区：`TOTAL` 单独加重，不要埋在明细里。
5. 金额区：官方估算金额，按模型条目显示 `USD ESTIMATE` 或 `CNY ESTIMATE`；匹配不到价格时显示 `PRICE: UNMAPPED`。
6. 底部传播区：一句根据模型和当前对话总结生成的短 footer + ASCII 条形码 + receipt id。

## 默认宽度

默认 48 字符；可选 42、48、56、64。脚本必须保证每一行不超过指定宽度。

## 品牌头图方向

顶部 logo 按 Agent 工具决定，不按模型决定。感谢语按模型决定，不按 Agent 工具决定。

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

## 文案原则

- 票面字段保留小票感但提高可读性。通用稳定字段固定为：`Input Tokens`、`Output Tokens`、`Cache Read Tokens`、`TOTAL`。
- 分隔线要分强弱两级：粗主分隔线用于切主区域，细副分隔线用于承接表头和次区块，不要整张票只用一种横线。
- 可选字段固定为：`Reasoning Tokens`、`Cache Write Tokens`。有真实字段就显示，没有就省略。
- 不要打印来源不确定的字段。比如 `System Tokens`、`Tool Use Tokens` 不进入首版票面。
- 多币种价格必须保留来源口径。人民币模型可以显示 `RATE NOTE`，例如 `CN MAINLAND` 或 `ALIYUN CN`；MiMo 这类通过 OpenRouter 补价的模型显示 `OPENROUTER`，避免把平台公开价伪装成厂商直连账单。
- 感谢语里的模型/品牌名保留标准写法，例如 `ChatGPT`、`GLM`、`MiniMax`、`DeepSeek`，不要全部压成 `CHATGPT`。
- 条形码使用原版 `|` 细竖线组合，保持轻量的 ASCII 小票质感。
- 当前版本不做二维码；聊天小票和默认票面继续保留条形码 + receipt id 结构。
- 交互式终端里默认逐行打印 receipt；若输出被管道或脚本捕获，则默认整块输出。需要强制逐行时用 `--stream`，需要强制整块时用 `--no-stream`。聊天回复仍使用代码块保持等宽布局。
- 解释性中文不要放进票面，放在 Skill 回复正文里。
- footer 要短，有传播记忆点，并且要像“这次对话自己的句子”。实现上不要走固定整句抽签，也不要走一眼能看穿的槽位拼句；更合适的是按主题生成几种不同口吻的短吐槽，再结合当前对话摘要挑一句。
- 黑色幽默要可读，像模型在轻微吐槽用户，而不是像文案模板在套词。优先接近这类感觉：`REASONING WAS BILLED SEPARATELY.`、`THE LAST REVISION WAS NOT THE LAST.`、`THE PRICE TAG IS HONEST. THE PROCESS WAS NOT.`；不要生成前言不搭后语的句子。
- 默认语气限制在黑色幽默或暖心鼓励之间；显式 `--footer-tone` 仍然可以强制风格。
- footer 最多 2 行，每行控制在紧凑长度内，避免把小票下半区挤坏。
