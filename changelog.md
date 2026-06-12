# Changelog

## 2026-06-08

### Added

- Local-only launch flow centered on `--chat-reply`
- Printable HTML output at `/tmp/check-please.html`
- Skills CLI install instructions in all three README files
- `LICENSE` file with MIT terms
- Google Gemini pricing coverage for current supported text-token models

### Changed

- `--chat-reply` now opens printable HTML in the system browser and prints only a plain local fallback path, avoiding `file://` links that Electron hosts may capture in-app
- Main README now focuses on what the project is, how to use it, and a receipt preview
- Traditional Chinese README standardised on `收據` wording
- Cantonese README keeps `單`-first wording for its local copy
- Footer copy now comes from row-aligned localized lines instead of tone/category buckets
- Google pricing entries were refreshed to current official Gemini API names and rates

### Notes

- This project stays local-first by default; no hosted dashboard is required
- Share URLs remain optional and outside the main launch path
- The footer is inspired by `Hchen1218/token-receipt` and `chrishutchinson/claude-receipts`

## 2026-05-18

### Added

- Traditional Chinese receipt support via `--language zh-TW`
- Cantonese receipt support via `--language cantonese`
- HTML receipt language toggle now includes `EN / 繁中 / 廣東話`
- Traditional Chinese and Cantonese README files

### Changed

- CLI language help and skill trigger guidance now describe `en`, `zh-TW`, and `cantonese`
- Receipt validation now covers Traditional Chinese and Cantonese output

## 2026-05-05

### Added

- Unified `--chat-reply` mode for supported software, which returns the receipt code block and a local Printable HTML link in one shot
- HTML receipt language toggle (`EN / 繁中 / 廣東話`) outside the receipt body
- External HTML tip panel with `15% / 18% / 20% / 25%` presets
- Conditional `SUBTOTAL / TIP / GRAND TOTAL` rows that only appear after tip selection
- Tip controls now only appear for receipts with a real priced subtotal

### Changed

- HTML tip mode now replaces the original footer instead of appending a tail
- Tip-aware footer generation now follows a separate tone path from the default receipt
- HTML now uses raw footer lines for tip mode, which fixes Chinese spacing artifacts and keeps footer replacement clean
- Chinese tip footers were rewritten into a more checkout-like, more grateful voice instead of template-heavy phrasing
- Chinese tip footers now actually respond to style and bill-state signals instead of only scene + tip level
- English tip footers no longer keep repeating the product name as the sentence subject
- HTML language switching now updates the page-level `lang` state instead of only swapping the visible receipt

### Notes

- Tip controls stay outside the printable receipt surface until the user explicitly opts in
- Claude Code `SessionEnd` hook now follows the same text-plus-HTML reply path
- Default chat receipts still stay text-first; tips are currently an HTML-only interaction layer

## 2026-04-29

### Added

- Printable HTML export via `--output html`
- Quiet file output via `--write`
- Dual export support via `--write-html`, so text receipts can also drop a printable HTML file in the same run
- Embedded HTML logo assets for Codex and Trae
- Dedicated SVG logo path for Claude Code in HTML
- HTML smoke coverage in `scripts/validate_receipt.py`

### Changed

- Split receipt rendering into a shared `ReceiptView`, so text and HTML outputs use the same receipt data model
- Tuned HTML preview to look like a real receipt workflow: gray stage on screen, white paper when printed
- Switched HTML layout sizing to printer-like measurements for more stable print proportions
- Tightened HTML row layout so longer fields such as context usage stay on one line more reliably

### Notes

- Chat receipts remain the primary artifact
- HTML is still the secondary route for browser print preview and physical printer workflows
