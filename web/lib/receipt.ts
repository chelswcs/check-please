export type ReceiptLanguage = "en" | "zh-TW" | "cantonese";
export type AgentTool = "claude-code" | "codex" | "gemini" | "generic";

export type ReceiptRow = {
  label: string;
  value: string;
};

export type ReceiptLanguageView = {
  language: ReceiptLanguage;
  logoLabel: string;
  thanksLine: string;
  receiptIdLine: string;
  dateLine: string;
  summaryRows: ReceiptRow[];
  itemHeader: ReceiptRow;
  tokenRows: ReceiptRow[];
  totalRow: ReceiptRow;
  pricingRows: ReceiptRow[];
  footer: string;
};

export type TipOption = {
  percent: number;
  tipAmount: string;
  grandTotal: string;
  footer: string;
};

export type TipConfig = {
  subtotal: string;
  subtotalLabel: string;
  tipLabel: string;
  grandTotalLabel: string;
  options: TipOption[];
};

export type ReceiptPayload = {
  agentTool: AgentTool;
  receiptId: string;
  barcode: string;
  languages: Record<ReceiptLanguage, ReceiptLanguageView>;
  tip: Record<ReceiptLanguage, TipConfig | null>;
};

export const languageLabels: Record<ReceiptLanguage, string> = {
  en: "EN",
  "zh-TW": "繁中",
  cantonese: "廣東話",
};

export function normalizeLanguage(value: string): ReceiptLanguage {
  const normalized = value.trim().toLowerCase();
  if (["zh", "zh-tw", "zh_tw", "tw", "zh-hk", "zh_hk", "繁體", "繁中"].includes(normalized)) {
    return "zh-TW";
  }
  if (["cantonese", "cantonese-hant", "cantonese_hant", "廣東話"].includes(normalized)) {
    return "cantonese";
  }
  return "en";
}
