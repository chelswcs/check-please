# Check Please 觸發詞

目標唔係只有用戶講出 `receipt` 時先觸發，而係把「想睇呢次對話 token / context / 成本收據」嘅表達都穩穩接住。

## 強觸發

呢啲講法預設應該直接調用 `check-please`：

- `check please`
- `埋單`
- `結帳`
- `發票`
- `打單`
- `token receipt`
- `token 收據`
- `對話發票`
- `AI 用量帳單`
- `token bill`
- `usage receipt`
- `cost receipt`
- `print token receipt`
- `把這次對話打成收據`
- `看看這輪 token 消耗`
- `生成本次對話 token 收據`
- `查看本次對話 Token 消耗`
- `繁體中文 token 收據`
- `廣東話 token 單`
- `廣東話 token receipt`

## 弱觸發

呢啲講法如果上下文明顯係想要「可以展示嘅收據」，都應該觸發：

- `context 用咗幾多`
- `呢輪使咗幾多錢`
- `把 token 消耗印出嚟`
- `畀張 token checkout 我`
- `本次對話成本`
- `這次上下文用了多少`
- `把這次 AI 用量做成發票`
- `用繁體中文出收據`
- `用廣東話出單`

## Claude Code 自動觸發

Claude Code 嘅 `SessionEnd` auto-trigger 唔依賴觸發詞；會話結束之後自動出單。

但喺會話中途，下面呢啲詞仍然應該觸發手動出單：

- `check please`
- `token receipt`
- `receipt`
- `埋單`
- `對話發票`
- `AI 用量帳單`

## 避免誤觸發

下面呢啲情況唔好直接觸發：

- 用戶只係討論緊 `pricing strategy`，冇要目前對話嘅帳單
- 用戶只係泛談 `token` 或 `context window`
- 用戶要嘅係表格、CSV、統計分析，而唔係收據形式
