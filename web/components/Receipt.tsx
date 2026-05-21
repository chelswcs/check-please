"use client";

import { useMemo, useState } from "react";
import type { AgentTool, ReceiptLanguage, ReceiptLanguageView, ReceiptPayload, TipOption } from "../lib/receipt";
import { languageLabels } from "../lib/receipt";

type ReceiptProps = {
  payload: ReceiptPayload;
  initialLanguage?: ReceiptLanguage;
};

const languageOrder: ReceiptLanguage[] = ["en", "zh-TW", "cantonese"];

function ClaudeCodeLogo() {
  return (
    <svg className="receipt-logo-svg receipt-logo-svg--claude-code" viewBox="0 0 128 76" aria-hidden="true" focusable="false">
      <g fill="currentColor" shapeRendering="crispEdges">
        <rect x="22" y="4" width="84" height="22" />
        <rect x="10" y="30" width="108" height="14" />
        <rect x="24" y="44" width="80" height="14" />
        <rect x="30" y="60" width="8" height="12" />
        <rect x="48" y="60" width="8" height="12" />
        <rect x="78" y="60" width="8" height="12" />
        <rect x="96" y="60" width="8" height="12" />
      </g>
      <g fill="#ffffff" shapeRendering="crispEdges">
        <rect x="38" y="12" width="10" height="14" />
        <rect x="80" y="12" width="10" height="14" />
      </g>
    </svg>
  );
}

function GeminiLogo() {
  return (
    <svg className="receipt-logo-svg receipt-logo-svg--gemini" viewBox="0 0 96 96" aria-hidden="true" focusable="false">
      <path d="M48 5c4 24 19 39 43 43-24 4-39 19-43 43C44 67 29 52 5 48 29 44 44 29 48 5Z" fill="currentColor" />
      <path d="M48 23c3 14 11 22 25 25-14 3-22 11-25 25-3-14-11-22-25-25 14-3 22-11 25-25Z" fill="#fff" />
    </svg>
  );
}

function GenericLogo({ label }: { label: string }) {
  return <div className="receipt-generic-logo">{label === "GEMINI" ? "✦" : "[ AI CHECKOUT ]"}</div>;
}

function Logo({ agentTool, label }: { agentTool: AgentTool; label: string }) {
  return (
    <div className="receipt-logo-shell">
      {agentTool === "claude-code" ? <ClaudeCodeLogo /> : null}
      {agentTool === "codex" ? <img className="receipt-logo-image receipt-logo-image--codex" src="/assets/codex-logo.png" alt="" aria-hidden="true" /> : null}
      {agentTool === "gemini" ? <GeminiLogo /> : null}
      {agentTool === "generic" ? <GenericLogo label={label} /> : null}
    </div>
  );
}

function Rule({ strong = false }: { strong?: boolean }) {
  return <div className={`receipt-rule${strong ? " strong" : ""}`} />;
}

function Rows({ rows }: { rows: { label: string; value: string }[] }) {
  return rows.map((row) => (
    <div className="receipt-row" key={`${row.label}:${row.value}`}>
      <span className="receipt-label">{row.label}</span>
      <span className="receipt-value">{row.value}</span>
    </div>
  ));
}

function TipSummary({ view, tipOption }: { view: ReceiptLanguageView; tipOption: TipOption | null }) {
  if (!tipOption) return null;
  return (
    <section className="receipt-tip-summary">
      <Rule />
      <Rows rows={[{ label: view.language === "en" ? "SUBTOTAL" : "小計", value: "" }]} />
    </section>
  );
}

function ReceiptArticle({
  payload,
  view,
  active,
  tipOption,
}: {
  payload: ReceiptPayload;
  view: ReceiptLanguageView;
  active: boolean;
  tipOption: TipOption | null;
}) {
  const tip = payload.tip[view.language];
  const footer = tipOption?.footer ?? view.footer;
  return (
    <article className={`receipt${active ? "" : " receipt--hidden"}`} data-language={view.language} lang={view.language === "cantonese" ? "zh-HK" : view.language}>
      <header className="receipt-header">
        <Logo agentTool={payload.agentTool} label={view.logoLabel} />
        <div className="receipt-logo-label">{view.logoLabel}</div>
        <div className="receipt-thanks">{view.thanksLine}</div>
        <div className="receipt-meta">{view.receiptIdLine}</div>
        <div className="receipt-meta">{view.dateLine}</div>
      </header>

      <Rule strong />
      <Rows rows={view.summaryRows} />
      <Rule />
      <Rows rows={[view.itemHeader]} />
      <Rule />
      <Rows rows={view.tokenRows} />
      <Rule strong />
      <div className="receipt-total"><Rows rows={[view.totalRow]} /></div>
      <Rule />
      <Rows rows={view.pricingRows} />

      {tip && tipOption ? (
        <section className="receipt-tip-summary">
          <Rule />
          <Rows rows={[{ label: tip.subtotalLabel, value: tip.subtotal }]} />
          <Rows rows={[{ label: `${tip.tipLabel} (${tipOption.percent}%)`, value: tipOption.tipAmount }]} />
          <div className="receipt-total"><Rows rows={[{ label: tip.grandTotalLabel, value: tipOption.grandTotal }]} /></div>
        </section>
      ) : null}

      <footer className="receipt-footer">
        <Rule strong />
        <div className="receipt-footer-line">{footer}</div>
        <pre className="receipt-barcode" aria-hidden="true">{payload.barcode}</pre>
        <div className="receipt-barcode-id">{payload.receiptId}</div>
      </footer>
    </article>
  );
}

export function Receipt({ payload, initialLanguage = "en" }: ReceiptProps) {
  const [language, setLanguage] = useState<ReceiptLanguage>(initialLanguage);
  const [tipEnabled, setTipEnabled] = useState(false);
  const [selectedPercent, setSelectedPercent] = useState<number | null>(null);

  const activeTip = payload.tip[language];
  const selectedTip = useMemo(() => {
    if (!tipEnabled || !activeTip || selectedPercent === null) return null;
    return activeTip.options.find((option) => option.percent === selectedPercent) ?? null;
  }, [activeTip, selectedPercent, tipEnabled]);

  return (
    <div className="receipt-page">
      <div className="print-toolbar">
        <button className="print-button" type="button" onClick={() => window.print()}>Print receipt</button>
      </div>

      {languageOrder.map((lang) => (
        <ReceiptArticle
          active={lang === language}
          key={lang}
          payload={payload}
          tipOption={lang === language ? selectedTip : null}
          view={payload.languages[lang]}
        />
      ))}

      <section className="receipt-language-panel" aria-label="Receipt language">
        <div className="receipt-language-controls">
          {languageOrder.map((lang) => (
            <button
              className={`language-option${lang === language ? " is-selected" : ""}`}
              key={lang}
              type="button"
              aria-pressed={lang === language}
              onClick={() => {
                setLanguage(lang);
                setSelectedPercent(null);
              }}
            >
              {languageLabels[lang]}
            </button>
          ))}
        </div>
      </section>

      {activeTip ? (
        <section className="receipt-tip-panel">
          <section className="receipt-tip-controls" aria-label="Tip controls">
            <label className="tip-toggle">
              <input
                type="checkbox"
                suppressHydrationWarning
                checked={tipEnabled}
                onChange={(event) => {
                  setTipEnabled(event.target.checked);
                  if (!event.target.checked) setSelectedPercent(null);
                }}
              />
              <span>{language === "en" ? "Add tip" : language === "zh-TW" ? "加一點小費" : "加少少貼士"}</span>
            </label>
            {tipEnabled ? (
              <div className="tip-options">
                {activeTip.options.map((option) => (
                  <button
                    className={`tip-option${option.percent === selectedPercent ? " is-selected" : ""}`}
                    key={option.percent}
                    type="button"
                    aria-pressed={option.percent === selectedPercent}
                    onClick={() => setSelectedPercent(option.percent)}
                  >
                    {option.percent}%
                  </button>
                ))}
              </div>
            ) : null}
          </section>
        </section>
      ) : null}
    </div>
  );
}
