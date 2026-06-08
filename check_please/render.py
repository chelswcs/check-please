"""Receipt rendering for token receipt."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import time
from typing import List, Tuple

from .models import (
    ALLOWED_WIDTHS,
    DEFAULT_LANGUAGE,
    PriceEstimate,
    UsageSnapshot,
    canonical_language,
    center_text_visual,
    display_time,
    fmt_int,
    normalize,
    parse_iso,
    printable_receipt_char,
    truncate_visual,
    visual_char_width,
    visual_display_width,
)


FOOTER_COPY_PATH = Path(__file__).with_name("footer_copy.json")


LABELS = {
    "en": {
        "generic_logo": "[ AI CHECKOUT ]",
        "thanks": "THANK YOU FOR CODING WITH {product}",
        "receipt_id": "RECEIPT #: {rid}",
        "date": "DATE: {date}",
        "provider": "PROVIDER",
        "model": "MODEL",
        "context": "CONTEXT USED",
        "item": "ITEM",
        "tokens": "TOKENS",
        "input": "Input Tokens",
        "output": "Output Tokens",
        "cached": "Cache Read Tokens",
        "reasoning": "Reasoning Tokens",
        "cache_write": "Cache Write Tokens",
        "total": "TOTAL",
        "token_unit": "TOKENS",
        "estimate": "{currency} ESTIMATE",
        "price": "PRICE",
        "price_date": "PRICE DATE",
        "rate_note": "RATE NOTE",
        "unmapped": "UNMAPPED",
    },
    "zh-TW": {
        "generic_logo": "[ AI 結帳 ]",
        "thanks": "感謝使用 {product}",
        "receipt_id": "收據號碼: {rid}",
        "date": "日期: {date}",
        "provider": "供應商",
        "model": "模型",
        "context": "已用上下文",
        "item": "項目",
        "tokens": "TOKEN",
        "input": "輸入 Tokens",
        "output": "輸出 Tokens",
        "cached": "快取讀取",
        "reasoning": "推理 Tokens",
        "cache_write": "快取寫入",
        "total": "總計",
        "token_unit": "Tokens",
        "estimate": "{currency} 預估",
        "price": "價格對應",
        "price_date": "價格日期",
        "rate_note": "價格說明",
        "unmapped": "未對應",
    },
    "cantonese": {
        "generic_logo": "[ AI 埋單 ]",
        "thanks": "多謝使用 {product}",
        "receipt_id": "單號: {rid}",
        "date": "日期: {date}",
        "provider": "供應商",
        "model": "模型",
        "context": "已用上下文",
        "item": "項目",
        "tokens": "TOKEN",
        "input": "輸入 Tokens",
        "output": "輸出 Tokens",
        "cached": "快取讀取",
        "reasoning": "推理 Tokens",
        "cache_write": "快取寫入",
        "total": "總數",
        "token_unit": "Tokens",
        "estimate": "{currency} 估算",
        "price": "價格對應",
        "price_date": "價格日期",
        "rate_note": "價格說明",
        "unmapped": "未對應",
    },
}


@dataclass(frozen=True)
class ReceiptRow:
    label: str
    value: str


@dataclass(frozen=True)
class ReceiptView:
    language: str
    width: int
    logo_lines: Tuple[str, ...]
    logo_label: str
    thanks_line: str
    receipt_id_line: str
    date_line: str
    summary_rows: Tuple[ReceiptRow, ...]
    item_header: ReceiptRow
    token_rows: Tuple[ReceiptRow, ...]
    total_row: ReceiptRow
    pricing_rows: Tuple[ReceiptRow, ...]
    footer_lines: Tuple[str, ...]
    barcode_line: str
    barcode_id_line: str


class Receipt:
    def __init__(self, width: int, language: str = DEFAULT_LANGUAGE) -> None:
        if width not in ALLOWED_WIDTHS:
            raise SystemExit(f"--width must be one of {ALLOWED_WIDTHS}")
        self.width = width
        self.language = canonical_language(language)
        self.lines: List[str] = []

    def add(self, text: str = "") -> None:
        self.lines.append(truncate_visual(text, self.width, self.language))

    def center(self, text: str = "") -> None:
        self.add(center_text_visual(text, self.width, self.language))

    def rule(self, char: str = "-") -> None:
        self.add(char * self.width)

    def strong_rule(self) -> None:
        self.rule("━")

    def light_rule(self) -> None:
        self.rule("─")

    def kv(self, left: str, right: str) -> None:
        right = str(right)
        right_width = visual_display_width(right, self.language)
        max_left = max(1, int(self.width - right_width - 1))
        left = truncate_visual(left, max_left, self.language)
        left_width = visual_display_width(left, self.language)
        spaces = max(1, int(math.floor(self.width - left_width - right_width)))
        self.add(left + " " * spaces + right)

    def blank(self) -> None:
        self.add("")

    def text(self) -> str:
        for line in self.lines:
            if visual_display_width(line, self.language) > self.width + 0.51:
                raise AssertionError(f"line exceeds width: {line!r}")
            for char in line:
                if not printable_receipt_char(char):
                    raise AssertionError(f"unsupported control character: {line!r}")
        return "\n".join(self.lines)


def labels_for(language: str) -> dict[str, str]:
    return LABELS[canonical_language(language)]


def receipt_id(snapshot: UsageSnapshot, provider: str) -> str:
    stamp = parse_iso(snapshot.timestamp)
    if stamp:
        date_part = stamp.strftime("%Y%m%d_%H%M%S")
    else:
        date_part = time.strftime("%Y%m%d_%H%M%S")
    seed = f"{snapshot.session_id}:{snapshot.provider}:{snapshot.model}:{snapshot.total_tokens}:{snapshot.source}:{date_part}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6].upper()
    nk = normalize(provider)
    prefix = (
        "CC"
        if nk == "anthropic"
        else "CX"
        if nk == "openai"
        else "KM"
        if nk == "moonshot"
        else "AI"
    )
    return f"{prefix}_{date_part}_{digest}"


def barcode(seed: str, width: int) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    patterns = ["|", "||", "| ", " ||", "|||", " |"]
    raw = "".join(patterns[int(char, 16) % len(patterns)] for char in digest)
    target = min(width - 8, max(24, width - 16))
    return center_text_visual(raw[:target], width, "en")


def auto_brand(provider: str, source: str, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    provider_key = normalize(provider)
    source_key = normalize(source)
    src_slash = source.replace("\\", "/").lower()
    if "#ses_" in source or source.startswith("opencode://"):
        return "opencode"
    if "/.kimi/sessions/" in src_slash or "/.kimi/imported_sessions/" in src_slash:
        return "kimi-code"
    if provider_key == "trae" or "trae" in source_key:
        return "trae"
    if provider_key == "openai" or "codex" in source_key:
        return "codex"
    if provider_key == "anthropic" or "claude" in source_key:
        return "claude-code"
    return "generic"


def add_centered_block(receipt: Receipt, lines: List[str], offset: int = 0) -> None:
    nonempty = [line for line in lines if line.strip()]
    shared_indent = min((len(line) - len(line.lstrip(" ")) for line in nonempty), default=0)
    normalized = [line[shared_indent:] for line in lines]
    block_width = max(visual_display_width(line.rstrip(), receipt.language) for line in normalized)
    left_pad = max(int(round((receipt.width - block_width) / 2)) + offset, 0)
    for line in normalized:
        receipt.add(" " * left_pad + line.rstrip())


def logo_block(agent_tool: str, language: str) -> tuple[Tuple[str, ...], str, int]:
    if agent_tool == "codex":
        return (
            (
                "      █████",
                "    █    ██   ███",
                "  ███ ██    ██   █",
                "██ ██ ██████   ███",
                "█  ██ ██    ███   █",
                "██   ███    █  ██  █",
                "  ███   █████  ██ ██",
                "  █   ██    █  ███",
                "   ███   ██    █",
                "         █████",
            ),
            "CODEX",
            0,
        )
    if agent_tool == "trae":
        return (
            (
                "   ██████████████",
                "███▒▒▒▒▒▒▒▒▒▒▒▒▒▒███",
                "███▒▒██████████▒▒███",
                "███▒▒██▒▒▒█▒▒▒█▒▒███",
                "███▒▒██████████▒▒███",
                "█████▒▒▒▒▒▒▒▒▒▒▒▒███",
                "   █████████████",
            ),
            "TRAE",
            0,
        )
    if agent_tool == "claude-code":
        return (
            (
                " ▐▛███▜▌",
                "▝▜█████▛▘",
                "  ▘▘ ▝▝",
            ),
            "CLAUDE CODE",
            -1,
        )
    if agent_tool == "kimi-code":
        return (
            (
                "       █▀▀▀▀▀▀▀█",
                "       █ ██▀ ██ █",
                "       █ ▀▀█▀▀ ██",
                "       █ █ ▄ █ ██",
                "       █ ██▄██ █▀",
                "        ▀▀▀▀▀▀▀",
            ),
            "KIMI CODE",
            0,
        )
    if agent_tool == "opencode":
        return (
            (
                "       ███████████████",
                "       █       █    ██",
                "       █ ████ ██ ████",
                "       █       █    ██",
                "       ███████████████",
            ),
            "OPENCODE",
            0,
        )
    return ((), labels_for(language)["generic_logo"], 0)


def add_logo(receipt: Receipt, agent_tool: str, language: str) -> None:
    lines, label, offset = logo_block(agent_tool, language)
    if lines:
        add_centered_block(receipt, list(lines), offset=offset)
        receipt.center(label)
        return
    receipt.center(label)


def product_name(snapshot: UsageSnapshot) -> str:
    model_key = normalize(snapshot.model)
    provider_key = normalize(snapshot.provider)
    if "claude" in model_key:
        return "Claude"
    if "codex" in model_key:
        return "Codex"
    if "gpt" in model_key:
        return "ChatGPT"
    if "gemini" in model_key or provider_key == "google":
        return "Gemini"
    if "deepseek" in model_key or provider_key == "deepseek":
        return "DeepSeek"
    if "kimi" in model_key or provider_key == "moonshot":
        return "Kimi"
    if "glm" in model_key or provider_key in ("zhipu", "bigmodel"):
        return "GLM"
    if "mimo" in model_key or provider_key == "xiaomi":
        return "MiMo"
    if "qwen" in model_key or provider_key in ("qwen", "dashscope", "alibaba"):
        return "Qwen"
    if "minimax" in model_key or provider_key == "minimax":
        return "MiniMax"
    if "trae" in model_key:
        return "Trae"
    if snapshot.model and snapshot.model != "UNRECORDED":
        return truncate_visual(snapshot.model, 16, "en")
    if provider_key == "anthropic":
        return "Claude"
    if provider_key == "openai":
        return "ChatGPT"
    return "AI"


def context_used(snapshot: UsageSnapshot) -> str:
    if snapshot.context_tokens is not None:
        used_src = snapshot.context_tokens
    else:
        used_src = snapshot.input_tokens
    used = fmt_int(used_src)
    if snapshot.context_window:
        return f"{used}/{fmt_int(snapshot.context_window)}"
    return used


def choose(options: List[str], digest: int, shift: int = 0) -> str:
    if not options:
        raise ValueError("choose() requires at least one option")
    return options[(digest >> shift) % len(options)]


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def footer_theme(snapshot: UsageSnapshot, hint: str) -> str:
    text = f"{hint} {snapshot.model} {snapshot.provider}".lower()
    visual = (
        "logo", "logos", "visual", "layout", "pixel", "pixels", "align", "alignment",
        "brand", "receipt", "poster", "icon", "视觉", "視覺", "像素", "对齐", "對齊", "排版", "居中", "小票", "收據", "传播", "傳播",
    )
    pricing = (
        "price", "pricing", "cost", "invoice", "bill", "estimate", "usd", "cny",
        "价格", "價格", "成本", "账单", "帳單", "張單", "條數", "发票", "發票", "美元", "人民币", "人民幣", "定价", "定價", "價錢",
    )
    debug = (
        "bug", "debug", "fix", "patch", "broken", "repair", "rollback", "validate",
        "报错", "修复", "失败", "验证", "回退", "报修",
    )
    shipping = (
        "ship", "launch", "release", "deploy", "publish", "上线", "发布", "交付", "落地",
    )
    iteration = (
        "tweak", "polish", "revise", "review", "iterate", "replace",
        "打磨", "微调", "微調", "迭代", "修改", "替换", "替換", "优化", "優化", "改版", "再改",
    )
    reasoning = (
        "reason", "reasoning", "thinking", "chain", "proof", "推理", "思考", "链路", "证明",
    )
    context = (
        "context", "cache", "prompt", "memory", "上下文", "缓存", "提示词", "记忆",
    )
    if contains_any(text, visual):
        return "visual"
    if contains_any(text, pricing):
        return "pricing"
    if contains_any(text, debug):
        return "debug"
    if contains_any(text, shipping):
        return "shipping"
    if contains_any(text, iteration):
        return "iteration"
    if snapshot.reasoning_output_tokens or contains_any(text, reasoning):
        return "reasoning"
    if snapshot.cached_input_tokens or snapshot.context_window or contains_any(text, context):
        return "context"
    return "generic"


def footer_style(snapshot: UsageSnapshot, tone: str, hint: str, digest: int, language: str = DEFAULT_LANGUAGE) -> str:
    language = canonical_language(language)
    if tone in ("snarky", "encouraging", "dry"):
        return tone
    text = f"{hint} {snapshot.model} {snapshot.provider}".lower()
    warm = ("ship", "launch", "release", "publish", "上线", "发布", "交付", "落地", "完成")
    sharp = (
        "logo", "visual", "layout", "price", "pricing", "bill", "debug", "fix", "align",
        "打磨", "对齐", "對齊", "价格", "價格", "账单", "帳單", "張單", "修复", "修復", "验证", "驗證", "回退", "替换", "替換", "迭代",
    )
    if contains_any(text, warm):
        return "encouraging"
    if language in {"zh-TW", "cantonese"}:
        if contains_any(text, sharp):
            return "snarky"
        return "dry" if digest % 4 == 0 else "snarky"
    if contains_any(text, sharp):
        return "snarky"
    return "encouraging" if digest % 2 == 0 else "snarky"


def footer_topic(theme: str, hint: str, digest: int) -> str:
    text = hint.lower()
    if theme == "visual":
        if contains_any(text, ("align", "alignment", "对齐", "居中", "位置", "空隙")):
            options = ["ALIGNMENT", "LAYOUT", "PIXELS"]
        elif contains_any(text, ("logo", "icon", "brand", "header", "像素", "螃蟹")):
            options = ["LOGO", "PIXELS", "LAYOUT"]
        else:
            options = ["LAYOUT", "LOGO", "PIXELS", "ALIGNMENT"]
    elif theme == "pricing":
        options = ["PRICE TAG", "BILL", "ESTIMATE", "RECEIPT"]
    elif theme == "debug":
        options = ["FIX", "PATCH", "REGRESSION", "RECEIPT"]
    elif theme == "shipping":
        options = ["OUTPUT", "RELEASE", "BUILD", "DELIVERY"]
    elif theme == "iteration":
        options = ["TWEAK", "REVISION", "LAYOUT", "DRAFT"]
    elif theme == "reasoning":
        options = ["THINKING", "PROOF", "ANSWER", "REASONING"]
    elif theme == "context":
        options = ["CONTEXT", "CACHE", "PROMPT", "WINDOW"]
    else:
        options = ["RECEIPT", "OUTPUT", "CHAT", "DRAFT"]
    return choose(options, digest, 8)


def footer_scene(theme: str, hint: str) -> str:
    text = hint.lower()
    scene_keywords = (
        ("logo", ("logo", "icon", "brand", "header", "螃蟹", "像素", "图标")),
        ("footer", ("footer", "文案", "标语", "结尾", "收尾", "punchline")),
        ("preview", ("preview", "align", "alignment", "layout", "spacing", "居中", "对齐", "预览", "间距", "版式")),
        ("print", ("html", "print", "printer", "打印", "热敏纸", "纸张", "receipt html")),
        ("receipt", ("receipt", "bill", "invoice", "小票", "账单", "票面")),
        ("trigger", ("trigger", "hook", "sessionend", "自动触发", "触发词", "hook")),
        ("readme", ("readme", "docs", "documentation", "文档", "预览块")),
        ("pricing", ("pricing", "price", "estimate", "cost", "价格", "预估", "计价", "成本")),
    )
    for scene, words in scene_keywords:
        if contains_any(text, words):
            return scene
    if theme == "visual":
        return "preview"
    if theme == "pricing":
        return "pricing"
    if theme == "shipping":
        return "receipt"
    if theme == "debug":
        return "trigger" if contains_any(text, ("hook", "trigger", "自动触发")) else "receipt"
    return "generic"


def footer_snark_candidates(theme: str, topic: str, brand: str) -> List[str]:
    if theme == "visual":
        return [
            f"YOU SPENT TOKENS ARGUING WITH {topic}.",
            f"THE {topic} WON. THE BUDGET DID NOT.",
            f"WE USED CONTEXT TO NEGOTIATE WITH {topic}.",
            f"THE {topic} LOOKS CALM. THE BILL DOES NOT.",
            f"THIS {topic} COST MORE THAN IT LOOKS.",
        ]
    if theme == "pricing":
        return [
            f"YOU ASKED FOR A {topic}. THE TOKENS OBJECTED.",
            f"THE {topic} IS HONEST. THE PROCESS WAS NOT.",
            f"THE {topic} ARRIVED BEFORE CONSENSUS DID.",
            "THE RECEIPT IS CLEAR. THE DAMAGE IS ITEMIZED.",
            "WE COUNTED THE TOKENS. THE BILL KEPT SCORE.",
        ]
    if theme == "debug":
        return [
            "THE PATCH WORKED. THE RECEIPT KEPT SCORE.",
            "YOU BOUGHT A FIX. THE TOKENS REMEMBER.",
            "THE REGRESSION LEFT. THE BILL STAYED.",
            "THE FIX WAS CHEAPER THAN DENIAL.",
            "WE SPENT TOKENS PROVING THE FIX MATTERED.",
        ]
    if theme == "shipping":
        return [
            "IT SHIPPED. THE TOKENS WILL NEVER FORGET.",
            "THE OUTPUT IS LIVE. THE RECEIPT HAS NOTES.",
            "DELIVERY SUCCEEDED. THE BILL STAYED.",
            "THE BUILD LANDED. ACCOUNTING DID NOT SMILE.",
        ]
    if theme == "iteration":
        return [
            "ONE MORE TWEAK COST EXACTLY THIS MUCH.",
            "THE LAST REVISION WAS NOT THE LAST.",
            "WE BOUGHT POLISH BY THE TOKEN.",
            f"THIS {topic} ONLY LOOKS FINAL.",
            "THE DRAFT CHARGED AGAIN.",
        ]
    if theme == "reasoning":
        return [
            "REASONING WAS BILLED SEPARATELY.",
            "THE ANSWER WAS SHORT. THE THINKING WAS NOT.",
            "THE PROOF LOOKED CHEAP. REASONING WAS NOT.",
            "SECOND THOUGHTS WERE NOT FREE.",
            "THE ANSWER ARRIVED. THE THINKING SENT A BILL.",
        ]
    if theme == "context":
        return [
            "WE SPENT CONTEXT SO YOU COULD SAY 'ONE MORE TWEAK.'",
            "CACHE SAVED MONEY. PERFECTION DID NOT.",
            "THE CONTEXT WINDOW HELD. BARELY.",
            "YOU PAID TOKENS TO REMEMBER THIS MUCH.",
            "THE PROMPT GOT LONGER. THE PATIENCE DID NOT.",
        ]
    return [
        "THE RECEIPT IS HONEST. THE PROCESS WAS DRAMATIC.",
        "YOU BOUGHT CLARITY. THE TOKENS PAID RETAIL.",
        "THIS LOOKS EFFORTLESS. THE BILL DISAGREES.",
        "THE OUTPUT IS CLEAN. THE RECEIPT KNOWS WHY.",
        f"{brand} DID THE WORK. THE BILL WROTE NOTES.",
    ]


def footer_dry_candidates(theme: str, topic: str, brand: str) -> List[str]:
    if theme == "visual":
        return [
            "THE LOGO MOVED. THE RECEIPT RECORDED IT.",
            "ALIGNMENT CHANGED. ACCOUNTING NOTED IT.",
            "PIXELS WERE USED. THE BILL CONFIRMS IT.",
        ]
    if theme == "pricing":
        return [
            "THE ESTIMATE EXISTS. SO DOES THE OUTPUT.",
            "THE BILL IS ATTACHED TO REAL TOKENS.",
            "THE RECEIPT REMEMBERS WHAT THIS COST.",
        ]
    if theme == "debug":
        return [
            "THE FIX EXISTS. THE RECEIPT CONFIRMS IT.",
            "THE PATCH LANDED. ACCOUNTING AGREED.",
            "THE BILL NOTED THE REGRESSION.",
        ]
    if theme == "shipping":
        return [
            "DELIVERY OCCURRED. THE BILL REMAINS.",
            "THE OUTPUT SHIPPED. THE RECEIPT NOTED IT.",
        ]
    if theme == "iteration":
        return [
            "THE REVISION EXISTS. THE RECEIPT PROVES IT.",
            "THE TWEAK LANDED. THE BILL IS ATTACHED.",
        ]
    if theme == "reasoning":
        return [
            "THE THINKING USED TOKENS. THE BILL AGREES.",
            "REASONING OCCURRED. THE RECEIPT NOTED IT.",
        ]
    if theme == "context":
        return [
            "CONTEXT WAS USED. THE RECEIPT CONFIRMS IT.",
            "CACHE PARTICIPATED. ACCOUNTING APPROVED.",
        ]
    return [
        "THE TOKENS WERE USED. THE RECEIPT CONFIRMS IT.",
        "THIS OUTPUT HAS A BILL.",
        f"{brand} FINISHED. THE RECEIPT LOGGED IT.",
    ]


def footer_encouraging_candidates(theme: str, topic: str, brand: str) -> List[str]:
    if theme == "visual":
        return [
            "THE PIXELS ARE QUIET NOW. KEEP GOING.",
            "THE LAYOUT FINALLY BREATHES. GOOD CALL.",
            "YOU SPENT TOKENS. THE SCREENSHOT GOT BETTER.",
            "THE LOGO SETTLED DOWN. SO DID THE RECEIPT.",
        ]
    if theme == "pricing":
        return [
            "THE BILL IS HONEST. SO IS THE RESULT.",
            "YOU PAID FOR CLARITY. THAT PART MATTERS.",
            "THE ESTIMATE IS CLEAR. THE WORK IS REAL.",
            "THE PRICE TAG IS CLEAN. KEEP BUILDING.",
        ]
    if theme == "debug":
        return [
            "THE FIX COST TOKENS. THE CALM WAS INCLUDED.",
            "YOU PAID FOR A FIX. YOU KEPT THE MOMENTUM.",
            "THE PATCH HELD. SO DID THE DIRECTION.",
        ]
    if theme == "shipping":
        return [
            "THE OUTPUT LANDED. KEEP THE MOMENTUM.",
            "DELIVERY COST TOKENS. THE RESULT MOVED.",
        ]
    if theme == "iteration":
        return [
            "THE TWEAK COST TOKENS. THE TASTE IMPROVED.",
            "THE REVISION LANDED. THE RECEIPT LOOKS LIGHTER.",
        ]
    if theme == "reasoning":
        return [
            "THE THINKING TOOK TOKENS. THE ANSWER EARNED THEM.",
            "THE PROOF COST SOMETHING. IT WAS WORTH IT.",
            "REASONING TOOK ITS TIME. CLARITY STAYED.",
        ]
    if theme == "context":
        return [
            "THE CONTEXT HELD. SO DID THE IDEA.",
            "CACHE SAVED TIME. YOU KEPT THE DIRECTION.",
            "THE WINDOW WAS TIGHT. THE RESULT STILL FIT.",
        ]
    return [
        "THE TOKENS LEFT. THE MOMENTUM STAYED.",
        "YOU SPENT CONTEXT. THE RESULT KEPT THE CHANGE.",
        "THIS COST TOKENS. IT ALSO MOVED.",
        f"{brand} KEPT GOING. SO DID YOU.",
    ]


def footer_bill_state(snapshot: UsageSnapshot, estimate: PriceEstimate) -> str:
    if snapshot.reasoning_output_tokens and snapshot.reasoning_output_tokens >= max(64, snapshot.output_tokens // 3):
        return "reasoning_heavy"
    if snapshot.input_tokens and snapshot.cached_input_tokens >= max(1, snapshot.input_tokens // 2):
        return "cache_heavy"
    amount = float(estimate.amount or 0.0)
    if amount >= 0.5:
        return "heavy"
    if amount >= 0.1:
        return "medium"
    return "light"


def tip_state(percent: float | int | None) -> str:
    value = float(percent or 0.0)
    if value <= 0:
        return "none"
    if value >= 25:
        return "lavish"
    if value >= 20:
        return "generous"
    if value >= 18:
        return "standard"
    return "polite"


def en_tip_subject(scene: str, brand: str) -> str:
    if scene == "logo":
        return "THE LOGO"
    if scene == "footer":
        return "THE SIGN-OFF"
    if scene == "preview":
        return "THE PREVIEW"
    if scene == "print":
        return "THE PRINT VIEW"
    if scene == "receipt":
        return "THE RECEIPT"
    if scene == "trigger":
        return "THE TRIGGER"
    if scene == "readme":
        return "THE README"
    if scene == "pricing":
        return "THE PRICE TAG"
    return brand


def en_tip_footer_candidates(scene: str, style: str, bill_state: str, current_tip_state: str, brand: str) -> List[str]:
    _ = scene
    _ = brand
    if current_tip_state == "polite":
        if style == "snarky":
            lines = [
                "FINALLY SETTLED. THAT TIP WAS SMALL BUT CORRECT.",
                "HELD TOGETHER. THE REGISTER CALLS THAT POLITE.",
                "LANDED CLEAN. SMALL KINDNESS NOTED.",
            ]
        elif style == "dry":
            lines = [
                "IN PLACE NOW. A POLITE GRATUITY WAS RECORDED.",
                "STABLE ENOUGH. SMALL SUPPORT WAS APPLIED.",
                "READY TO GO. THE TIP ENTRY WAS ACCEPTED.",
            ]
        else:
            lines = [
                "IN A BETTER PLACE NOW. THANKS FOR THE EXTRA NOD.",
                "SETTLED DOWN. THAT LITTLE BIT OF KINDNESS HELPED.",
                "LOOKING RIGHT NOW. POLITE SUPPORT RECEIVED.",
            ]
    elif current_tip_state == "standard":
        if style == "snarky":
            lines = [
                "FINALLY LANDED. STANDARD KINDNESS ACCEPTED.",
                "LOOKS RIGHT NOW. THE COUNTER APPROVES.",
                "STOPPED ARGUING. GRATUITY NOTED WITHOUT DRAMA.",
            ]
        elif style == "dry":
            lines = [
                "NOW STABLE. STANDARD GRATUITY APPLIED.",
                "SETTLED AT LAST. STANDARD TIP RECORDED.",
                "READY FOR CHECKOUT. THE EXTRA WAS APPROVED.",
            ]
        else:
            lines = [
                "FINALLY FEELS COMPLETE. THANKS, THAT WAS THE RIGHT KIND OF GENEROUS.",
                "LOOKS BETTER NOW. SOLID GRATUITY. GOOD FORM.",
                "HELD UP WELL. STANDARD KINDNESS LANDED.",
            ]
    elif current_tip_state == "generous":
        if style == "snarky":
            lines = [
                "LOOKS EXPENSIVE IN THE RIGHT WAY. GENEROSITY DETECTED.",
                "FINALLY BEHAVED. THE REGISTER FELT THAT ONE.",
                "CAME TOGETHER. THIS TIP HAD OPINIONS.",
            ]
        elif style == "dry":
            lines = [
                "NOW SETTLED. GENEROSITY RECORDED.",
                "IN GOOD SHAPE. HIGH GRATUITY APPLIED.",
                "READY FOR PRINT. THE EXTRA WAS NOTED.",
            ]
        else:
            lines = [
                "LOOKS GOOD NOW. THANKS, THE CLERK FEELS SEEN.",
                "FINALLY LANDED. THIS WAS GENEROUS IN A USEFUL WAY.",
                "IN PLACE NOW. THE EXTRA LANDED WELL.",
            ]
    else:
        if style == "snarky":
            lines = [
                "LOCKED IN. THIS WAS LESS A TIP THAN A POSITION.",
                "FINALLY HAS ITS SHAPE. THE REGISTER GOT THE MESSAGE.",
                "LANDED HARD. THAT GRATUITY MADE THE POINT CLEAR.",
            ]
        elif style == "dry":
            lines = [
                "NOW FINAL. A LARGE GRATUITY WAS APPLIED.",
                "COMPLETE AT LAST. LAVISH SUPPORT WAS RECORDED.",
                "READY TO CLOSE. THE EXTRA EXCEEDED NORMAL CHECKOUT.",
            ]
        else:
            lines = [
                "FEELS COMPLETE NOW. THANKS, THAT WAS OPENLY KIND.",
                "FINALLY LOOKS RIGHT. THIS RECEIPT WILL REMEMBER YOU FONDLY.",
                "LANDED WELL. THE COUNTER APPRECIATES THE COMMITMENT.",
            ]

    if bill_state == "heavy":
        lines.append("TOOK A REAL BILL TO GET HERE. THE EXTRA STILL LOOKS DELIBERATE.")
    elif bill_state == "reasoning_heavy":
        lines.append("COST A FAIR BIT OF THINKING. THE GRATUITY STILL LANDED CLEAN.")
    elif bill_state == "cache_heavy":
        lines.append("CACHE DID SOME OF THE LIFTING. THE EXTRA STILL COUNTS.")
    return lines


def cantonese_tip_footer_candidates(
    scene: str,
    style: str,
    bill_state: str,
    current_tip_state: str,
    brand: str,
    digest: int,
) -> List[str]:
    _ = brand
    scene_name = {
        "logo": "Logo",
        "footer": "收尾",
        "preview": "預覽",
        "print": "打印效果",
        "receipt": "張單",
        "trigger": "觸發邏輯",
        "readme": "README",
        "pricing": "價錢呢欄",
    }.get(scene, "呢一版")
    base = {
        "polite": [
            f"{scene_name}順咗少少，貼士到位啱啱好。",
            "心意唔算高，張單即刻識得笑。",
            "收銀台收到，語氣即刻冇咁燥。",
        ],
        "standard": [
            f"{scene_name}終於企穩，貼士落袋有分數。",
            "呢筆落得穩，張票即刻識做人。",
            "收銀台有分寸，知道你係識貨人。",
        ],
        "generous": [
            f"{scene_name}有晒排場，貼士一落即刻響。",
            "呢一下夠大方，張單都識轉腔。",
            "收銀台代佢講，多謝講到有迴響。",
        ],
        "lavish": [
            f"{scene_name}有晒光，呢筆唔係貼士係登場。",
            "呢一下夠份量，成張票都似升堂。",
            "收銀台即刻轉方向，笑到連墨都發光。",
        ],
    }[current_tip_state]
    style_lines = {
        "snarky": [
            "錢唔係白畀，張單即刻識收皮。",
            "貼士一落嚟，張單都識講道理。",
        ],
        "dry": [
            "額外已入數，票面有記錄。",
            "貼士已確認，收銀台好清醒。",
        ],
        "encouraging": [
            "心意嚟得啱，結果都順眼。",
            "場面補得返，節奏未行散。",
        ],
    }.get(style, [])
    bill_lines = {
        "heavy": ["張單本身唔細，貼士仲夠 face。"],
        "reasoning_heavy": ["諗到腦都出煙，貼士幫佢收返先。"],
        "cache_heavy": ["快取幫手慳，貼士照樣計一單。"],
    }.get(bill_state, [])
    candidates = base + style_lines + bill_lines
    rotate = digest % max(len(candidates), 1)
    return candidates[rotate:] + candidates[:rotate]


def zh_tw_tip_footer_candidates(
    scene: str,
    style: str,
    bill_state: str,
    current_tip_state: str,
    brand: str,
    digest: int,
) -> List[str]:
    _ = brand
    scene_name = {
        "logo": "Logo",
        "footer": "結尾",
        "preview": "預覽",
        "print": "列印版",
        "receipt": "這張收據",
        "trigger": "觸發流程",
        "readme": "README",
        "pricing": "價格這欄",
    }.get(scene, "這一版")
    base = {
        "polite": [
            f"{scene_name}順了，小費也到位了。",
            "心意不算多，但收據有感受。",
            "這一筆剛剛好，語氣也柔軟了。",
        ],
        "standard": [
            f"{scene_name}穩了，這筆給得很剛好。",
            "小費一進來，整張收據都比較會做人。",
            "這筆不浮誇，但很懂場面。",
        ],
        "generous": [
            f"{scene_name}有精神了，這筆真的有誠意。",
            "這一下很大方，收銀台都不好意思再臭臉。",
            "小費一到，整張單都亮了一點。",
        ],
        "lavish": [
            f"{scene_name}有排面了，這已經不是小費，是抬轎。",
            "這筆下去，收據都想站起來敬禮。",
            "出手太明顯，連總額都變得有禮貌。",
        ],
    }[current_tip_state]
    style_lines = {
        "snarky": [
            "錢不是白花，至少收據閉嘴了。",
            "這筆一進來，帳單也學會看場合。",
        ],
        "dry": [
            "額外金額已入帳，票面確認。",
            "小費成立，收銀台確認。",
        ],
        "encouraging": [
            "心意來得剛好，結果也更順眼。",
            "場面補回來了，節奏也還在。",
        ],
    }.get(style, [])
    bill_lines = {
        "heavy": ["本來就不便宜，這筆反而更有意思。"],
        "reasoning_heavy": ["這輪想很多，這筆算幫它收尾。"],
        "cache_heavy": ["快取省了一點，小費還是另外算。"],
    }.get(bill_state, [])
    candidates = base + style_lines + bill_lines
    rotate = digest % max(len(candidates), 1)
    return candidates[rotate:] + candidates[:rotate]


def auto_tip_footer(
    snapshot: UsageSnapshot,
    estimate: PriceEstimate,
    tone: str,
    width: int,
    language: str,
    hint: str = "",
    tip_percent: float | int = 0,
) -> str:
    return fit_footer_text(
        auto_tip_footer_line(snapshot, estimate, tone, language, hint, tip_percent),
        width,
        language,
    )


def auto_tip_footer_line(
    snapshot: UsageSnapshot,
    estimate: PriceEstimate,
    tone: str,
    language: str,
    hint: str = "",
    tip_percent: float | int = 0,
) -> str:
    language = canonical_language(language)
    current_tip_state = tip_state(tip_percent)
    if current_tip_state == "none":
        return auto_footer_line(snapshot, estimate, tone, language, hint)

    key = (
        f"tip:{language}:{snapshot.provider}:{snapshot.model}:{snapshot.total_tokens}:"
        f"{snapshot.cached_input_tokens}:{snapshot.reasoning_output_tokens}:{hint}:{tone}:"
        f"{estimate.status}:{estimate.amount}:{tip_percent}"
    )
    digest = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16)
    theme = footer_theme(snapshot, hint)
    scene = footer_scene(theme, hint)
    style = footer_style(snapshot, tone, hint, digest, language)
    bill_state = footer_bill_state(snapshot, estimate)
    brand = product_name(snapshot).upper()

    if language == "zh-TW":
        return choose(zh_tw_tip_footer_candidates(scene, style, bill_state, current_tip_state, brand, digest), digest, 18)
    if language == "cantonese":
        return choose(cantonese_tip_footer_candidates(scene, style, bill_state, current_tip_state, brand, digest), digest, 18)

    return choose(en_tip_footer_candidates(scene, style, bill_state, current_tip_state, brand), digest, 18)


@lru_cache(maxsize=1)
def load_footer_copy() -> dict[str, object]:
    with FOOTER_COPY_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("footer"), (dict, list)):
        raise ValueError(f"Invalid footer copy data in {FOOTER_COPY_PATH}")
    return data


def localized_footer_line(language: str, digest: int) -> str:
    footer = load_footer_copy()["footer"]
    if not isinstance(footer, list):
        raise KeyError("Footer copy is not row-based")
    rows = [row for row in footer if isinstance(row, dict) and isinstance(row.get(language), str)]
    if not rows:
        raise KeyError(f"Missing footer copy for language {language!r}")
    return str(rows[(digest >> 14) % len(rows)][language])


def localized_footer_candidates(language: str, style: str, theme: str) -> List[str]:
    footer = load_footer_copy()["footer"]
    if not isinstance(footer, dict):
        raise ValueError(f"Invalid footer copy data in {FOOTER_COPY_PATH}")
    language_copy = footer.get(language)
    if not isinstance(language_copy, dict):
        raise KeyError(f"Missing footer copy for language {language!r}")

    candidates = language_copy.get(theme) or language_copy.get("default")
    if isinstance(candidates, list) and all(isinstance(item, str) for item in candidates):
        return candidates

    # Backward compatibility for the older language -> tone -> category shape.
    style_copy = language_copy.get(style)
    if not isinstance(style_copy, dict):
        raise KeyError(f"Missing footer copy for {language!r}/{style!r}")
    candidates = style_copy.get(theme) or style_copy.get("default")
    if not isinstance(candidates, list) or not all(isinstance(item, str) for item in candidates):
        raise ValueError(f"Invalid footer copy list for {language!r}/{style!r}/{theme!r}")
    return candidates


def split_display_text(text: str, max_width: int, language: str) -> tuple[str, str]:
    left: list[str] = []
    width = 0.0
    index = 0
    for index, char in enumerate(text):
        char_width = visual_char_width(char, language)
        if width + char_width > max_width:
            break
        left.append(char)
        width += char_width
    else:
        return text, ""
    return "".join(left).rstrip(), text[index:].lstrip()


def fit_footer_text(text: str, width: int, language: str) -> str:
    language = canonical_language(language)
    max_line = min(width, 40)
    normalized = re.sub(r"\s+", " ", text.strip())
    if visual_display_width(normalized, language) <= max_line:
        return normalized

    words = normalized.split()
    if len(words) > 1:
        for split_at in range(len(words) - 1, 0, -1):
            left = " ".join(words[:split_at])
            right = " ".join(words[split_at:])
            if visual_display_width(left, language) <= max_line and visual_display_width(right, language) <= max_line:
                return left + "\n" + right

    left, right = split_display_text(normalized, max_line, language)
    if not right:
        return left
    return left + "\n" + truncate_visual(right, max_line, language)


def auto_footer_line(snapshot: UsageSnapshot, estimate: PriceEstimate, tone: str, language: str, hint: str = "") -> str:
    language = canonical_language(language)
    key = f"{snapshot.provider}:{snapshot.model}:{snapshot.total_tokens}:{snapshot.cached_input_tokens}:{snapshot.reasoning_output_tokens}:{hint}:{tone}:{estimate.status}"
    digest = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16)
    try:
        return localized_footer_line(language, digest)
    except KeyError:
        pass

    theme = footer_theme(snapshot, hint)
    style = footer_style(snapshot, tone, hint, digest, language)
    brand = product_name(snapshot).upper()
    topic = footer_topic(theme, hint, digest)
    if style == "snarky":
        candidates = footer_snark_candidates(theme, topic, brand)
    elif style == "dry":
        candidates = footer_dry_candidates(theme, topic, brand)
    else:
        candidates = footer_encouraging_candidates(theme, topic, brand)
    return choose(candidates, digest, 14)


def auto_footer(snapshot: UsageSnapshot, estimate: PriceEstimate, tone: str, width: int, language: str, hint: str = "") -> str:
    return fit_footer_text(auto_footer_line(snapshot, estimate, tone, language, hint), width, language)


def footer_lines(text: str, width: int, language: str) -> List[str]:
    language = canonical_language(language)
    normalized = text.replace("\\n", "\n")
    lines: List[str] = []
    for raw in normalized.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        if language == "en":
            raw = raw.upper()
        lines.append(truncate_visual(raw, width, language))
    return lines or [""]


def source_has(snapshot: UsageSnapshot, field: str) -> bool:
    return field in snapshot.available_fields


def currency_symbol(currency: str) -> str:
    key = currency.upper()
    if key == "USD":
        return "$"
    if key in ("CNY", "RMB"):
        return "¥"
    return f"{key} "


def money(amount: float | None, currency: str = "USD") -> str:
    if amount is None:
        return "UNMAPPED"
    if 0 < amount < 0.000001:
        return f"<{currency_symbol(currency)}0.000001"
    return f"{currency_symbol(currency)}{amount:.6f}"


def build_receipt_view(
    snapshot: UsageSnapshot,
    estimate: PriceEstimate,
    width: int,
    agent_tool: str,
    footer: str,
    footer_tone: str,
    conversation_hint: str,
    language: str = DEFAULT_LANGUAGE,
) -> ReceiptView:
    language = canonical_language(language)
    labels = labels_for(language)
    provider = snapshot.provider.upper() if snapshot.provider else "UNKNOWN"
    rid = receipt_id(snapshot, snapshot.provider)
    footer_text = auto_footer(snapshot, estimate, footer_tone, width, language, conversation_hint) if footer == "auto" else footer

    summary_rows = (
        ReceiptRow(labels["provider"], provider),
        ReceiptRow(labels["model"], snapshot.model),
        ReceiptRow(labels["context"], context_used(snapshot)),
    )
    token_rows: list[ReceiptRow] = []
    if source_has(snapshot, "input_tokens"):
        token_rows.append(ReceiptRow(labels["input"], fmt_int(snapshot.input_tokens)))
    if source_has(snapshot, "output_tokens"):
        token_rows.append(ReceiptRow(labels["output"], fmt_int(snapshot.output_tokens)))
    if source_has(snapshot, "cached_input_tokens"):
        token_rows.append(ReceiptRow(labels["cached"], fmt_int(snapshot.cached_input_tokens)))
    if source_has(snapshot, "reasoning_output_tokens"):
        token_rows.append(ReceiptRow(labels["reasoning"], fmt_int(snapshot.reasoning_output_tokens)))
    if source_has(snapshot, "cache_write_tokens"):
        token_rows.append(ReceiptRow(labels["cache_write"], fmt_int(snapshot.cache_write_tokens)))

    pricing_rows = [
        ReceiptRow(labels["estimate"].format(currency=estimate.currency), money(estimate.amount, estimate.currency)),
        ReceiptRow(labels["price"], labels["unmapped"] if estimate.status == "UNMAPPED" else estimate.model),
    ]
    if estimate.status != "UNMAPPED":
        if estimate.source_checked_at:
            pricing_rows.append(ReceiptRow(labels["price_date"], estimate.source_checked_at))
        if estimate.rate_note:
            pricing_rows.append(ReceiptRow(labels["rate_note"], estimate.rate_note))

    logo_lines, logo_label, _ = logo_block(agent_tool, language)
    return ReceiptView(
        language=language,
        width=width,
        logo_lines=logo_lines,
        logo_label=logo_label,
        thanks_line=labels["thanks"].format(product=product_name(snapshot)),
        receipt_id_line=labels["receipt_id"].format(rid=rid),
        date_line=labels["date"].format(date=display_time(snapshot.timestamp)),
        summary_rows=summary_rows,
        item_header=ReceiptRow(labels["item"], labels["tokens"]),
        token_rows=tuple(token_rows),
        total_row=ReceiptRow(labels["total"], f"{fmt_int(snapshot.total_tokens)} {labels['token_unit']}"),
        pricing_rows=tuple(pricing_rows),
        footer_lines=tuple(footer_lines(footer_text, width, language)),
        barcode_line=barcode(rid, width),
        barcode_id_line=rid,
    )


def render_receipt(
    snapshot: UsageSnapshot,
    estimate: PriceEstimate,
    width: int,
    agent_tool: str,
    footer: str,
    footer_tone: str,
    conversation_hint: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    view = build_receipt_view(snapshot, estimate, width, agent_tool, footer, footer_tone, conversation_hint, language)
    receipt = Receipt(width, view.language)

    add_logo(receipt, agent_tool, view.language)
    receipt.blank()
    receipt.center(view.thanks_line)
    receipt.center(view.receipt_id_line)
    receipt.center(view.date_line)
    receipt.strong_rule()
    for row in view.summary_rows:
        receipt.kv(row.label, row.value)
    receipt.light_rule()
    receipt.kv(view.item_header.label, view.item_header.value)
    receipt.light_rule()
    for row in view.token_rows:
        receipt.kv(row.label, row.value)
    receipt.strong_rule()
    receipt.kv(view.total_row.label, view.total_row.value)
    receipt.light_rule()
    for row in view.pricing_rows:
        receipt.kv(row.label, row.value)
    receipt.strong_rule()
    for line in view.footer_lines:
        receipt.center(line)
    receipt.blank()
    receipt.add(view.barcode_line)
    receipt.center(view.barcode_id_line)
    return receipt.text()


def print_receipt(text: str, stream: bool, delay: float) -> None:
    if not stream:
        print(text)
        return
    for line in text.splitlines():
        print(line, flush=True)
        if delay > 0:
            time.sleep(delay)
