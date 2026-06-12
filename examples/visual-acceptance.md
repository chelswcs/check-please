# Check Please 視覺驗收

人工驗收時先睇視覺，唔好先睇欄位清單。

## 必須通過

- 一眼似熱感紙收據，而唔係普通表格。
- 喺聊天入面調用時，預設回覆應該直接係完整 receipt 本體，而唔係「已處理」「已輸出」或者欄位摘要。
- 頂部有品牌感，可以區分 Codex / Claude Code / Generic。
- Claude Code 頂部使用縮細版 `█` block 像素螃蟹輪廓，成塊左邊緣同主體唔可以歪。
- 頂部 logo 按 Agent 工具決定；感謝語按實際模型決定。
- `TOTAL` 係視覺中心。
- 底部有根據模型/當前對話總結變化嘅 footer 同條碼，適合截圖分享。
- 終端運行時可以用 `--stream` 形成一行一行印出嚟嘅收據效果。
- 所有價格都有來源口徑；未知價格明確標註 `UNMAPPED`。
- 美元模型顯示 `USD ESTIMATE`，人民幣模型顯示 `CNY ESTIMATE`；有平台或區域口徑時顯示 `RATE NOTE`。
- Token 明細只包含已固定而且有來源嘅欄位：通用欄位 `Input Tokens`、`Output Tokens`、`Cache Read Tokens`、`TOTAL`；可選欄位 `Reasoning Tokens`、`Cache Write Tokens` 有就顯示。

## 應該拒絕

- Markdown 表格。
- 純 JSON / YAML / CSV。
- 只有 token 數字，冇收據形態。
- 聊天回覆入面先寫一段解釋，再貼收據，令視覺被打斷。
- 只返回 `RECEIPT #`、`TOTAL`、`USD ESTIMATE` 呢類摘錄，而唔係完整收據。
- 超闊換行令截圖唔好睇。
- 模型價格對應唔到時硬計美元。
- 輸出 `System Tokens`、`Tool Use Tokens` 或者其他未固定嘅數據項。
- 出現 `DATA: SNAPSHOT`。
