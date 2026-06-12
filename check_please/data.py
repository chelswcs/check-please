"""Data loading and pricing for token receipt."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from .models import (
    COMMON_TOKEN_FIELDS,
    OPTIONAL_TOKEN_FIELDS,
    RECEIPT_TOKEN_FIELDS,
    ModelCost,
    ModelUsage,
    PriceEstimate,
    UsageSnapshot,
    as_int,
    normalize,
    parse_iso,
)


def iter_session_files() -> Iterable[Path]:
    home = Path.home()
    roots = [
        home / ".codex" / "sessions",
        home / ".codex" / "archived_sessions",
    ]
    for root in roots:
        if not root.exists():
            continue
        yield from root.rglob("*.jsonl")


def newest_session_file() -> Optional[Path]:
    files = list(iter_session_files())
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def find_codex_session_for_thread(thread_id: str) -> Optional[Path]:
    if not thread_id:
        return None
    matches: list[Path] = []
    for root in (Path.home() / ".codex" / "sessions", Path.home() / ".codex" / "archived_sessions"):
        if not root.exists():
            continue
        matches.extend(root.rglob(f"*{thread_id}.jsonl"))
    if matches:
        return max(matches, key=lambda path: path.stat().st_mtime)
    for path in iter_session_files():
        try:
            with path.open("r", encoding="utf-8") as handle:
                first = handle.readline()
            item = json.loads(first)
        except (OSError, json.JSONDecodeError):
            continue
        payload = item.get("payload") or {}
        if item.get("type") == "session_meta" and str(payload.get("id") or "") == thread_id:
            return path
    return None


def iter_claude_transcripts() -> Iterable[Path]:
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return
    yield from projects_dir.rglob("*.jsonl")


def find_claude_transcript_for_session(session_id: str) -> Optional[Path]:
    if not session_id:
        return None
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None
    matches = list(projects_dir.rglob(f"{session_id}.jsonl"))
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def newest_claude_transcript() -> Optional[Path]:
    files = list(iter_claude_transcripts())
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def is_claude_transcript_file(path: Path) -> bool:
    if path.suffix != ".jsonl" or not path.is_file():
        return False
    if "/.claude/projects/" in str(path.resolve()).replace("\\", "/"):
        return True
    try:
        with path.open("r", encoding="utf-8") as handle:
            for _ in range(50):
                line = handle.readline()
                if not line:
                    break
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(item, dict):
                    continue
                message = item.get("message")
                if isinstance(message, dict) and isinstance(message.get("usage"), dict):
                    return True
    except OSError:
        return False
    return False


def load_snapshot_from_claude_transcript(
    path: Path,
    scope: str,
    model_override: Optional[str],
    provider_override: Optional[str],
) -> UsageSnapshot:
    turns: list[tuple[Optional[str], str, tuple[int, int, int, int]]] = []
    session_id = path.stem
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            sid = item.get("sessionId")
            if isinstance(sid, str) and sid.strip():
                session_id = sid.strip()
            message = item.get("message")
            if not isinstance(message, dict):
                continue
            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue
            raw_model = str(message.get("model") or "")
            counts = (
                as_int(usage.get("input_tokens")),
                as_int(usage.get("cache_read_input_tokens")),
                as_int(usage.get("cache_creation_input_tokens")),
                as_int(usage.get("output_tokens")),
            )
            # Claude Code writes zero-usage "<synthetic>" rows for UI-only messages.
            if raw_model.startswith("<") or not any(counts):
                continue
            model = raw_model.strip() or "UNRECORDED"
            turns.append(
                (
                    item.get("timestamp") if isinstance(item.get("timestamp"), str) else None,
                    model,
                    counts,
                )
            )

    if not turns:
        raise SystemExit(f"No assistant usage records found in Claude transcript {path}")

    selected = turns[-1:] if scope == "latest-turn" else turns
    uncached = sum(t[2][0] for t in selected)
    cached = sum(t[2][1] for t in selected)
    cache_write = sum(t[2][2] for t in selected)
    output = sum(t[2][3] for t in selected)
    model = model_override or turns[-1][1]
    provider = provider_override or infer_provider_from_model(model)
    # Anthropic usage reports uncached input only; receipt semantics expect
    # input_tokens to include cached reads and cache writes.
    input_tokens = uncached + cached + cache_write

    fields = ["input_tokens", "output_tokens", "total_tokens"]
    if cached:
        fields.append("cached_input_tokens")
    if cache_write:
        fields.append("cache_write_tokens")

    return UsageSnapshot(
        input_tokens=input_tokens,
        cached_input_tokens=cached,
        cache_write_tokens=cache_write,
        output_tokens=output,
        reasoning_output_tokens=0,
        total_tokens=input_tokens + output,
        provider=str(provider),
        model=str(model),
        source=str(path),
        session_id=session_id,
        timestamp=turns[-1][0],
        scope=scope,
        available_fields=tuple(sorted(set(fields))),
    )


def infer_provider_from_model(model: str) -> str:
    if not model or model == "UNRECORDED":
        return "unknown"
    model_lower = model.lower()
    if "claude" in model_lower:
        return "anthropic"
    if "gpt" in model_lower or model_lower.startswith("o"):
        return "openai"
    if "gemini" in model_lower:
        return "google"
    if "deepseek" in model_lower:
        return "deepseek"
    if "minimax" in model_lower or model_lower.startswith("m"):
        return "minimax"
    if "glm" in model_lower:
        return "zhipu"
    if "qwen" in model_lower:
        return "alibaba"
    if "mimo" in model_lower:
        return "xiaomi"
    return "unknown"


def maybe_model_from_meta(payload: Dict[str, Any]) -> Optional[str]:
    for key in ("model", "model_id", "model_name", "model_slug"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def maybe_model_from_turn_context(payload: Dict[str, Any]) -> Optional[str]:
    value = payload.get("model")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def model_from_env() -> Optional[str]:
    for key in ("CODEX_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "MODEL"):
        value = os.environ.get(key)
        if value:
            return value.strip()
    return None


_OPENCODE_VENDOR_TO_PROVIDER = {
    "anthropic": "anthropic",
    "openai": "openai",
    "google": "google",
    "deepseek": "deepseek",
    "zhipu": "zhipu",
    "glm": "zhipu",
    "bigmodel": "zhipu",
    "dashscope": "alibaba",
    "alibaba": "alibaba",
    "xiaomi": "xiaomi",
    "minimax": "minimax",
}


def billing_model_slug_from_opencode(model_id: str) -> str:
    mid = (model_id or "").strip()
    if not mid or mid.lower() == "unknown":
        return "UNRECORDED"
    if "/" in mid:
        tail = mid.split("/", 1)[1].strip()
        return tail or mid.replace("/", "_")
    return mid


def provider_and_slug_from_opencode_model(model_id_raw: str) -> tuple[str, str]:
    """Map OpenCode Models.dev ids (vendor/modelSlug) onto pricing lookup."""
    slug = billing_model_slug_from_opencode(model_id_raw)
    if "/" in model_id_raw:
        vendor = model_id_raw.split("/", 1)[0].strip().lower()
        prov = _OPENCODE_VENDOR_TO_PROVIDER.get(vendor)
        if prov:
            return prov, slug
    return infer_provider_from_model(slug), slug


def opencode_standard_dirs(home: Optional[Path] = None) -> list[Path]:
    """OpenCode SQLite 存放目錄候選（對齊 CodeBurn opencode.ts getDataDir 思路 + Windows LOCALAPPDATA）。"""
    seen: Dict[str, Path] = {}

    def add(p: Path) -> None:
        key = str(p)
        if key not in seen:
            seen[key] = p

    root = home or Path.home()
    oe = os.environ.get("OPENCODE_DATA_DIR", "").strip()
    if oe:
        add(Path(os.path.expandvars(os.path.expanduser(oe))))
    xd = os.environ.get("XDG_DATA_HOME", "").strip()
    if xd:
        add(Path(os.path.expandvars(os.path.expanduser(xd))) / "opencode")
    add(root / ".local" / "share" / "opencode")
    if os.name == "nt":
        la = os.environ.get("LOCALAPPDATA", "").strip()
        if la:
            add(Path(la) / "opencode")
    return list(seen.values())


def iter_opencode_db_files() -> Iterable[Path]:
    for d in opencode_standard_dirs():
        if not d.is_dir():
            continue
        try:
            for name in sorted(os.listdir(d)):
                if name.startswith("opencode") and name.endswith(".db"):
                    p = d / name
                    if p.is_file():
                        yield p
        except OSError:
            continue


def _opencode_db_has_session_message(conn: sqlite3.Connection) -> bool:
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('session', 'message')"
        ).fetchone()
        return bool(n and n[0] >= 2)
    except sqlite3.Error:
        return False


def _opencode_list_root_sessions(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """返回 (session_id, time_created) 根會話，優先跳過子會話同歸檔欄位（如果唔存在就降級查詢）。"""
    queries = (
        "SELECT id, time_created FROM session WHERE time_archived IS NULL AND parent_id IS NULL ORDER BY time_created DESC",
        "SELECT id, time_created FROM session WHERE parent_id IS NULL ORDER BY time_created DESC",
        "SELECT id, time_created FROM session ORDER BY time_created DESC",
    )
    for sql in queries:
        try:
            rows = conn.execute(sql).fetchall()
            parsed: list[tuple[str, int]] = []
            for sid_raw, tc in rows:
                if isinstance(sid_raw, str) and sid_raw.strip():
                    parsed.append((sid_raw.strip(), as_int(tc)))
            return parsed
        except sqlite3.Error:
            continue
    return []


def find_opencode_session_in_db(db_path: Path, session_id: str) -> bool:
    if not db_path.is_file():
        return False
    try:
        conn = sqlite3.connect(str(db_path.resolve()), timeout=5.0)
    except sqlite3.Error:
        return False
    try:
        if not _opencode_db_has_session_message(conn):
            return False
        row = conn.execute(
            "SELECT 1 FROM session WHERE id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def global_newest_opencode_session() -> Optional[tuple[Path, str]]:
    best: Optional[tuple[Path, str, float]] = None
    for db_path in iter_opencode_db_files():
        try:
            conn = sqlite3.connect(str(db_path.resolve()), timeout=2.0)
        except sqlite3.Error:
            continue
        try:
            if not _opencode_db_has_session_message(conn):
                continue
            rows = _opencode_list_root_sessions(conn)
            if not rows:
                continue
            sid, tc = rows[0]
            # time_created：秒级或毫秒混用——与 CodeBurn 一致转成可排序 float
            tkey = float(tc) / 1000.0 if float(tc or 0) < 1e12 else float(tc)
            cand = (db_path, sid, tkey)
            if best is None or cand[2] > best[2]:
                best = cand
        finally:
            conn.close()
    if best is None:
        return None
    return best[0], best[1]


def global_find_opencode_db_for_session(session_id: str) -> Optional[Path]:
    for db_path in iter_opencode_db_files():
        if find_opencode_session_in_db(db_path, session_id):
            return db_path
    return None


def is_opencode_database_file(path: Path) -> bool:
    if not path.is_file():
        return False
    suf = path.suffix.lower()
    if suf != ".db":
        return False
    name_ok = path.name.startswith("opencode")
    low = path.name.lower()
    if not name_ok:
        path_slash = str(path.resolve()).replace("\\", "/").lower()
        name_ok = "opencode" in low and "/opencode/" in path_slash
    if not name_ok:
        return False
    try:
        conn = sqlite3.connect(str(path.resolve()), timeout=2.0)
    except sqlite3.Error:
        return False
    try:
        return _opencode_db_has_session_message(conn)
    finally:
        conn.close()


def _opencode_iso_from_tc(time_created_raw: Any) -> str:
    try:
        n = float(time_created_raw)
    except (TypeError, ValueError):
        return dt.datetime.now(dt.timezone.utc).isoformat()
    ms = n * 1000.0 if n < 1e12 else n
    return dt.datetime.fromtimestamp(ms / 1000.0, tz=dt.timezone.utc).isoformat()


def _assistant_tokens_from_payload(data: Dict[str, Any]) -> Optional[tuple[int, int, int, int, int]]:
    if data.get("role") != "assistant":
        return None
    raw_cost = data.get("cost")
    cost_ok = isinstance(raw_cost, (int, float)) and float(raw_cost) != 0.0
    t = data.get("tokens") or {}
    inp = as_int(t.get("input"))
    outp = as_int(t.get("output"))
    reasoning = as_int(t.get("reasoning"))
    cache = t.get("cache") if isinstance(t.get("cache"), dict) else {}
    cached_read = as_int(cache.get("read"))
    cache_write = as_int(cache.get("write"))
    if inp == outp == reasoning == cached_read == cache_write == 0 and not cost_ok:
        return None
    return (inp, cached_read, cache_write, outp, reasoning)


def load_snapshot_from_opencode_sqlite(
    db_path: Path,
    session_id: str,
    scope: str,
    model_override: Optional[str],
    provider_override: Optional[str],
) -> UsageSnapshot:
    try:
        conn = sqlite3.connect(str(db_path.resolve()), timeout=10.0)
    except sqlite3.Error as exc:
        raise SystemExit(f"Cannot open OpenCode database {db_path}: {exc}") from exc
    try:
        if not _opencode_db_has_session_message(conn):
            raise SystemExit(f"OpenCode DB schema mismatch (need session/message): {db_path}")
        try:
            rows = conn.execute(
                "SELECT time_created, data FROM message WHERE session_id = ? ORDER BY time_created ASC, rowid ASC",
                (session_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise SystemExit(f"OpenCode SQLite message read failed {db_path}: {exc}") from exc
    finally:
        conn.close()

    turns: list[tuple[Any, str, tuple[int, int, int, int, int]]] = []
    for time_created, raw in rows:
        if not isinstance(raw, str):
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        tup = _assistant_tokens_from_payload(payload)
        if tup is None:
            continue
        model_id_cell = payload.get("modelID")
        mid = model_id_cell.strip() if isinstance(model_id_cell, str) else ""
        turns.append((time_created, mid, tup))

    if not turns:
        raise SystemExit(
            f"No assistant rows with tokens/cost found in OpenCode DB for session={session_id!r}: {db_path}. "
            "Try `opencode session list`, set OPENCODE_SESSION_ID, or use --opencode-session-id."
        )

    if scope == "latest-turn":
        _, last_mid_raw, tup = turns[-1]
        last_mid = (last_mid_raw or "").strip()
        inp_s, cached_s, cw_s, outp_s, reas_s = tup
        last_ts_iso = _opencode_iso_from_tc(turns[-1][0])
        aggregated = tup
        model_pick_raw = model_override or last_mid
    else:
        sums = [0, 0, 0, 0, 0]
        for _, mid, tup in turns:
            for i, _v in enumerate(tup):
                sums[i] += tup[i]
        inp_s, cached_s, cw_s, outp_s, reas_s = sums[0], sums[1], sums[2], sums[3], sums[4]
        last_mid = (turns[-1][1] or "").strip()
        last_ts_iso = _opencode_iso_from_tc(turns[-1][0])
        aggregated = tuple(sums)
        model_pick_raw = model_override or last_mid

    raw_model_cell = ((model_pick_raw or "").strip()) or ""
    raw_model_final = raw_model_cell or model_from_env() or "UNRECORDED"
    vendor_provider, inferred_slug = provider_and_slug_from_opencode_model(raw_model_final)
    provider = provider_override or vendor_provider
    # 單面模型名優先用戶覆蓋；否則用 vendor/slug → 淨返 slug（同定價表對齊）
    if model_override and model_override.strip():
        mo = model_override.strip()
        model_line = billing_model_slug_from_opencode(mo) if "/" in mo else mo
    elif raw_model_final == "UNRECORDED":
        model_line = "UNRECORDED"
    else:
        model_line = inferred_slug

    pricing_model = model_override.strip() if model_override and model_override.strip() else inferred_slug

    total_agg = aggregated[0] + aggregated[1] + aggregated[2] + aggregated[3] + aggregated[4]

    fields: list[str] = []
    if inp_s > 0:
        fields.append("input_tokens")
    if cached_s > 0:
        fields.append("cached_input_tokens")
    if cw_s > 0:
        fields.append("cache_write_tokens")
    if outp_s > 0:
        fields.append("output_tokens")
    if reas_s > 0:
        fields.append("reasoning_output_tokens")
    fields.append("total_tokens")
    avail = tuple(sorted(set(fields)))

    source_ref = f"{db_path}#{session_id}"
    return UsageSnapshot(
        input_tokens=inp_s,
        cached_input_tokens=cached_s,
        cache_write_tokens=cw_s,
        output_tokens=outp_s,
        reasoning_output_tokens=reas_s,
        total_tokens=total_agg,
        context_tokens=None,
        context_window=None,
        provider=str(provider),
        model=str(pricing_model if pricing_model and pricing_model != "UNRECORDED" else model_line),
        source=source_ref,
        session_id=session_id,
        timestamp=last_ts_iso,
        scope=scope,
        available_fields=avail,
        skip_price_estimate=False,
    )


def runtime_opencode_session_id(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    runtime = env or os.environ
    for key in ("OPENCODE_SESSION_ID",):
        val = runtime.get(key, "").strip()
        if val:
            return val
    return None


def load_snapshot_from_session(path: Path, scope: str, model_override: Optional[str], provider_override: Optional[str]) -> UsageSnapshot:
    session_meta: Dict[str, Any] = {}
    token_event: Optional[Dict[str, Any]] = None
    token_timestamp: Optional[str] = None
    turn_context_model: Optional[str] = None

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            item_type = item.get("type")
            payload = item.get("payload") or {}
            if item_type == "session_meta" and isinstance(payload, dict):
                session_meta = payload
            if item_type == "turn_context" and isinstance(payload, dict):
                turn_context_model = maybe_model_from_turn_context(payload) or turn_context_model
            if item_type == "event_msg" and isinstance(payload, dict) and payload.get("type") == "token_count":
                token_event = payload
                token_timestamp = item.get("timestamp")

    if not token_event:
        raise SystemExit(f"No token_count event found in {path}")

    info = token_event.get("info") or {}
    usage_key = "total_token_usage" if scope == "session" else "last_token_usage"
    usage = info.get(usage_key) or {}
    available_fields = tuple(sorted(key for key in usage.keys() if isinstance(key, str)))
    provider = provider_override or session_meta.get("model_provider") or "unknown"
    model = (
        model_override
        or maybe_model_from_meta(session_meta)
        or turn_context_model
        or model_from_env()
        or "UNRECORDED"
    )
    session_id = str(session_meta.get("id") or path.stem)

    return UsageSnapshot(
        input_tokens=as_int(usage.get("input_tokens")),
        cached_input_tokens=as_int(usage.get("cached_input_tokens")),
        cache_write_tokens=as_int(usage.get("cache_write_tokens")),
        output_tokens=as_int(usage.get("output_tokens")),
        reasoning_output_tokens=as_int(usage.get("reasoning_output_tokens")),
        total_tokens=as_int(usage.get("total_tokens")),
        context_window=as_int(info.get("model_context_window")) or None,
        provider=str(provider),
        model=str(model),
        source=str(path),
        session_id=session_id,
        timestamp=token_timestamp or session_meta.get("timestamp"),
        scope=scope,
        available_fields=available_fields,
    )


def load_manual_snapshot(args: argparse.Namespace) -> UsageSnapshot:
    total = args.total_tokens
    if total is None:
        total = as_int(args.input_tokens) + as_int(args.output_tokens)
    available_fields = []
    if args.input_tokens is not None:
        available_fields.append("input_tokens")
    if args.output_tokens is not None:
        available_fields.append("output_tokens")
    if args.cached_input_tokens is not None:
        available_fields.append("cached_input_tokens")
    if args.cache_write_tokens is not None:
        available_fields.append("cache_write_tokens")
    if args.reasoning_output_tokens is not None:
        available_fields.append("reasoning_output_tokens")
    if total is not None:
        available_fields.append("total_tokens")

    return UsageSnapshot(
        input_tokens=as_int(args.input_tokens),
        cached_input_tokens=as_int(args.cached_input_tokens),
        cache_write_tokens=as_int(args.cache_write_tokens),
        output_tokens=as_int(args.output_tokens),
        reasoning_output_tokens=as_int(args.reasoning_output_tokens),
        total_tokens=as_int(total),
        context_window=as_int(args.context_window) or None,
        provider=args.provider or "unknown",
        model=args.model or model_from_env() or "UNRECORDED",
        source="manual",
        session_id=args.receipt_seed or "manual",
        timestamp=None,
        scope=args.scope,
        available_fields=tuple(sorted(set(available_fields))),
    )


class _DailyTally:
    """Accumulates per-model token usage across the sessions of one local day."""

    def __init__(self) -> None:
        self.models: Dict[str, Dict[str, Any]] = {}
        self._session_keys: set[str] = set()

    @property
    def session_count(self) -> int:
        return len(self._session_keys)

    def add_session(
        self,
        model: str,
        provider: str,
        input_tokens: int = 0,
        cached_input_tokens: int = 0,
        cache_write_tokens: int = 0,
        output_tokens: int = 0,
        reasoning_output_tokens: int = 0,
        total_tokens: Optional[int] = None,
        session_key: Optional[str] = None,
    ) -> None:
        key = model or "UNRECORDED"
        bucket = self.models.setdefault(
            key,
            {
                "provider": provider,
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "cache_write_tokens": 0,
                "output_tokens": 0,
                "reasoning_output_tokens": 0,
                "total_tokens": 0,
                "sessions": 0,
            },
        )
        bucket["input_tokens"] += input_tokens
        bucket["cached_input_tokens"] += cached_input_tokens
        bucket["cache_write_tokens"] += cache_write_tokens
        bucket["output_tokens"] += output_tokens
        bucket["reasoning_output_tokens"] += reasoning_output_tokens
        if total_tokens is None:
            total_tokens = (
                input_tokens + cached_input_tokens + cache_write_tokens + output_tokens + reasoning_output_tokens
            )
        bucket["total_tokens"] += total_tokens
        bucket["sessions"] += 1
        self._session_keys.add(session_key if session_key is not None else f"anon-{len(self._session_keys)}")

    def breakdown(self) -> tuple[ModelUsage, ...]:
        rows = [
            ModelUsage(
                model=model,
                provider=str(data["provider"]),
                input_tokens=int(data["input_tokens"]),
                cached_input_tokens=int(data["cached_input_tokens"]),
                cache_write_tokens=int(data["cache_write_tokens"]),
                output_tokens=int(data["output_tokens"]),
                reasoning_output_tokens=int(data["reasoning_output_tokens"]),
                total_tokens=int(data["total_tokens"]),
                sessions=int(data["sessions"]),
            )
            for model, data in self.models.items()
        ]
        return tuple(sorted(rows, key=lambda row: row.total_tokens, reverse=True))

    def to_snapshot(self, day: dt.date, source: str, skip_price_estimate: bool = False) -> UsageSnapshot:
        breakdown = self.breakdown()
        if not breakdown:
            raise SystemExit(f"No sessions with token usage found for {day.isoformat()} in {source}.")
        totals = {
            field: sum(getattr(row, field) for row in breakdown)
            for field in (
                "input_tokens",
                "cached_input_tokens",
                "cache_write_tokens",
                "output_tokens",
                "reasoning_output_tokens",
                "total_tokens",
            )
        }
        fields = [field for field, value in totals.items() if field != "total_tokens" and value > 0]
        fields.append("total_tokens")
        top = breakdown[0]
        return UsageSnapshot(
            input_tokens=totals["input_tokens"],
            cached_input_tokens=totals["cached_input_tokens"],
            cache_write_tokens=totals["cache_write_tokens"],
            output_tokens=totals["output_tokens"],
            reasoning_output_tokens=totals["reasoning_output_tokens"],
            total_tokens=totals["total_tokens"],
            provider=top.provider,
            model=top.model,
            source=source,
            session_id=f"daily-{day.isoformat()}",
            timestamp=dt.datetime.now().astimezone().isoformat(),
            scope="today",
            available_fields=tuple(sorted(set(fields))),
            skip_price_estimate=skip_price_estimate,
            model_breakdown=breakdown,
            session_count=self.session_count,
        )


def _local_date(value: Optional[str], fallback: Optional[float] = None) -> Optional[dt.date]:
    parsed = parse_iso(value)
    if parsed is not None:
        if parsed.tzinfo is None:
            return parsed.date()
        return parsed.astimezone().date()
    if fallback is not None:
        return dt.date.fromtimestamp(fallback)
    return None


def load_daily_snapshot_codex(
    day: dt.date,
    model_override: Optional[str],
    provider_override: Optional[str],
) -> UsageSnapshot:
    tally = _DailyTally()
    for path in iter_session_files():
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if dt.date.fromtimestamp(mtime) != day:
            continue
        session_meta: Dict[str, Any] = {}
        turn_context_model: Optional[str] = None
        token_event: Optional[Dict[str, Any]] = None
        token_timestamp: Optional[str] = None
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    item_type = item.get("type")
                    payload = item.get("payload") or {}
                    if item_type == "session_meta" and isinstance(payload, dict):
                        session_meta = payload
                    if item_type == "turn_context" and isinstance(payload, dict):
                        turn_context_model = maybe_model_from_turn_context(payload) or turn_context_model
                    if item_type == "event_msg" and isinstance(payload, dict) and payload.get("type") == "token_count":
                        token_event = payload
                        token_timestamp = item.get("timestamp")
        except OSError:
            continue
        if not token_event:
            continue
        if _local_date(token_timestamp, mtime) != day:
            continue
        usage = (token_event.get("info") or {}).get("total_token_usage") or {}
        model = (
            model_override
            or maybe_model_from_meta(session_meta)
            or turn_context_model
            or "UNRECORDED"
        )
        provider = provider_override or session_meta.get("model_provider") or infer_provider_from_model(model)
        tally.add_session(
            model=str(model),
            provider=str(provider),
            input_tokens=as_int(usage.get("input_tokens")),
            cached_input_tokens=as_int(usage.get("cached_input_tokens")),
            cache_write_tokens=as_int(usage.get("cache_write_tokens")),
            output_tokens=as_int(usage.get("output_tokens")),
            reasoning_output_tokens=as_int(usage.get("reasoning_output_tokens")),
            total_tokens=as_int(usage.get("total_tokens")) or None,
            session_key=str(path),
        )
    return tally.to_snapshot(day, "codex-sessions")


def load_daily_snapshot_claude(
    day: dt.date,
    model_override: Optional[str],
    provider_override: Optional[str],
) -> UsageSnapshot:
    tally = _DailyTally()
    for path in iter_claude_transcripts():
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        # Sessions are appended live, so only files touched on the target day can hold its usage.
        if dt.date.fromtimestamp(mtime) < day:
            continue
        per_model: Dict[str, list[tuple[int, int, int, int]]] = {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    message = item.get("message")
                    if not isinstance(message, dict):
                        continue
                    usage = message.get("usage")
                    if not isinstance(usage, dict):
                        continue
                    if _local_date(item.get("timestamp")) != day:
                        continue
                    raw_model = str(message.get("model") or "")
                    counts = (
                        as_int(usage.get("input_tokens")),
                        as_int(usage.get("cache_read_input_tokens")),
                        as_int(usage.get("cache_creation_input_tokens")),
                        as_int(usage.get("output_tokens")),
                    )
                    # Claude Code writes zero-usage "<synthetic>" rows for UI-only messages.
                    if raw_model.startswith("<") or not any(counts):
                        continue
                    model = model_override or (raw_model.strip() or "UNRECORDED")
                    per_model.setdefault(model, []).append(counts)
        except OSError:
            continue
        for model, turns in per_model.items():
            uncached = sum(t[0] for t in turns)
            cached = sum(t[1] for t in turns)
            cache_write = sum(t[2] for t in turns)
            output = sum(t[3] for t in turns)
            provider = provider_override or infer_provider_from_model(model)
            tally.add_session(
                model=model,
                provider=str(provider),
                # Anthropic usage reports uncached input only; receipt semantics expect
                # input_tokens to include cached reads and cache writes.
                input_tokens=uncached + cached + cache_write,
                cached_input_tokens=cached,
                cache_write_tokens=cache_write,
                output_tokens=output,
                session_key=str(path),
            )
    return tally.to_snapshot(day, "claude-transcripts")


def load_daily_snapshot_opencode(
    day: dt.date,
    model_override: Optional[str],
    provider_override: Optional[str],
) -> UsageSnapshot:
    tally = _DailyTally()
    for db_path in iter_opencode_db_files():
        try:
            conn = sqlite3.connect(str(db_path.resolve()), timeout=5.0)
        except sqlite3.Error:
            continue
        try:
            if not _opencode_db_has_session_message(conn):
                continue
            try:
                rows = conn.execute("SELECT session_id, time_created, data FROM message").fetchall()
            except sqlite3.Error:
                continue
        finally:
            conn.close()
        per_session: Dict[tuple[str, str], list[tuple[int, int, int, int, int]]] = {}
        for session_id, time_created, raw in rows:
            if not isinstance(raw, str):
                continue
            if _local_date(_opencode_iso_from_tc(time_created)) != day:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            tup = _assistant_tokens_from_payload(payload)
            if tup is None:
                continue
            model_cell = payload.get("modelID")
            mid = model_cell.strip() if isinstance(model_cell, str) else ""
            per_session.setdefault((str(session_id), mid), []).append(tup)
        for (session_id, mid), turns in per_session.items():
            sums = [sum(t[i] for t in turns) for i in range(5)]
            raw_model = model_override or mid or "UNRECORDED"
            vendor_provider, slug = provider_and_slug_from_opencode_model(raw_model)
            provider = provider_override or vendor_provider
            tally.add_session(
                model=slug if raw_model != "UNRECORDED" else "UNRECORDED",
                provider=str(provider),
                input_tokens=sums[0],
                cached_input_tokens=sums[1],
                cache_write_tokens=sums[2],
                output_tokens=sums[3],
                reasoning_output_tokens=sums[4],
                session_key=f"{db_path}:{session_id}",
            )
    return tally.to_snapshot(day, "opencode-db")


def load_daily_snapshot(agent_tool: Optional[str], args: argparse.Namespace) -> UsageSnapshot:
    day = dt.date.today()
    if agent_tool == "claude-code":
        return load_daily_snapshot_claude(day, args.model, args.provider)
    if agent_tool == "codex":
        return load_daily_snapshot_codex(day, args.model, args.provider)
    if agent_tool == "opencode":
        return load_daily_snapshot_opencode(day, args.model, args.provider)
    if agent_tool in MANUAL_ONLY_HOSTS:
        raise SystemExit(manual_mode_error(agent_tool))
    raise SystemExit(
        "Daily scope needs a single software source. "
        "Pass --agent-tool codex, --agent-tool claude-code, or --agent-tool opencode, "
        "or run check-please inside the software whose usage you want to bill."
    )


def has_manual_usage(args: argparse.Namespace) -> bool:
    return args.input_tokens is not None or args.output_tokens is not None or args.total_tokens is not None


def trae_storage_hints() -> tuple[str, ...]:
    home = Path.home()
    return (
        str(home / "Library" / "Application Support" / "Trae" / "User" / "workspaceStorage"),
        str(home / "Library" / "Application Support" / "Trae" / "User" / "globalStorage"),
        str(home / "Library" / "Application Support" / "Trae CN" / "User" / "workspaceStorage"),
        str(home / "Library" / "Application Support" / "Trae CN" / "User" / "globalStorage"),
        r"%APPDATA%\Trae\User\workspaceStorage",
        r"%APPDATA%\Trae\User\globalStorage",
        r"%APPDATA%\Trae CN\User\workspaceStorage",
        r"%APPDATA%\Trae CN\User\globalStorage",
    )


# Hosts check-please can brand on the receipt but cannot read usage logs for.
# The agent running inside these hosts should pass its own usage numbers manually.
MANUAL_ONLY_HOSTS = ("trae", "cursor", "manus", "antigravity")


def manual_mode_error(agent_tool: str) -> str:
    if agent_tool == "trae":
        hints = "\n".join(f"  - {path}" for path in trae_storage_hints())
        return (
            "Automatic Trae session import is not implemented yet.\n"
            "Trae stores chat state in app storage and workspace SQLite files rather than simple JSONL session logs.\n"
            "Known Trae storage locations include:\n"
            f"{hints}\n"
            "Use manual mode: provide --input-tokens and --output-tokens."
        )
    label = agent_tool or "this host"
    return (
        f"Automatic usage import for {label} is not implemented; it does not expose a stable local usage log. "
        f"Use manual mode: pass the usage you can see in {label} via "
        "--input-tokens / --output-tokens (and optionally --model / --provider), "
        f"keeping --agent-tool {label} so the receipt carries the right branding."
    )


def trae_manual_mode_error() -> str:
    return manual_mode_error("trae")


def runtime_agent_tool(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    runtime = env or os.environ
    if runtime.get("CLAUDECODE"):
        return "claude-code"
    if any(runtime.get(key) for key in ("CODEX_THREAD_ID", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "CODEX_SHELL")):
        return "codex"
    if any(runtime.get(key) for key in ("TRAE_RUNTIME", "TRAE_IDE", "TRAE_SESSION_ID")):
        return "trae"
    if runtime_opencode_session_id(runtime):
        return "opencode"
    return None


def runtime_claude_session_id(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    runtime = env or os.environ
    for key in ("CLAUDE_SESSION_ID",):
        value = runtime.get(key)
        if value:
            return value.strip()
    return None


def runtime_codex_thread_id(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    runtime = env or os.environ
    value = runtime.get("CODEX_THREAD_ID")
    if value:
        return value.strip()
    return None


def requested_agent_tool(args: argparse.Namespace, env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    explicit = getattr(args, "agent_tool", None)
    if explicit and explicit != "auto":
        return explicit

    brand = getattr(args, "brand", None)
    if brand in ("codex", "claude-code", "opencode") + MANUAL_ONLY_HOSTS:
        return brand

    return runtime_agent_tool(env)


def resolve_snapshot(args: argparse.Namespace) -> UsageSnapshot:
    if has_manual_usage(args):
        return load_manual_snapshot(args)

    if args.scope == "today":
        if args.session:
            raise SystemExit(
                "--scope today aggregates every session of the day, so it cannot be combined with --session. "
                "Drop --session, or use --scope session for a single file."
            )
        return load_daily_snapshot(requested_agent_tool(args), args)

    if args.session:
        if is_claude_transcript_file(args.session):
            return load_snapshot_from_claude_transcript(args.session, args.scope, args.model, args.provider)
        if is_opencode_database_file(args.session):
            ses = (getattr(args, "opencode_session_id", None) or "").strip() or runtime_opencode_session_id()
            if not ses:
                raise SystemExit(
                    "OpenCode: --session points to an OpenCode SQLite file. "
                    "Add --opencode-session-id <ses_...> or set OPENCODE_SESSION_ID."
                )
            return load_snapshot_from_opencode_sqlite(
                args.session, ses, args.scope, args.model, args.provider
            )
        return load_snapshot_from_session(args.session, args.scope, args.model, args.provider)

    agent_tool = requested_agent_tool(args)

    if agent_tool == "claude-code":
        session_id = runtime_claude_session_id()
        transcript = find_claude_transcript_for_session(session_id) if session_id else None
        if transcript is None:
            transcript = newest_claude_transcript()
        if transcript:
            return load_snapshot_from_claude_transcript(transcript, args.scope, args.model, args.provider)
        raise SystemExit(
            "No Claude Code transcripts found under ~/.claude/projects. "
            "If you are on Windows, the equivalent home-relative path is %USERPROFILE%\\.claude\\projects."
        )

    if agent_tool == "codex":
        session_path = None
        thread_id = runtime_codex_thread_id()
        if thread_id:
            session_path = find_codex_session_for_thread(thread_id)
        if session_path is None:
            session_path = newest_session_file()
        if session_path:
            return load_snapshot_from_session(session_path, args.scope, args.model, args.provider)
        raise SystemExit(
            "No Codex session file found under ~/.codex/sessions or ~/.codex/archived_sessions. "
            "If you are on Windows, the equivalent home-relative paths are %USERPROFILE%\\.codex\\sessions and %USERPROFILE%\\.codex\\archived_sessions."
        )

    if agent_tool == "opencode":
        ses = (getattr(args, "opencode_session_id", None) or "").strip() or runtime_opencode_session_id()
        if ses:
            db_hit = global_find_opencode_db_for_session(ses)
            if db_hit:
                return load_snapshot_from_opencode_sqlite(db_hit, ses, args.scope, args.model, args.provider)
            raise SystemExit(
                f"OpenCode session id {ses!r} not found in any opencode*.db under known data dirs. "
                "Try `opencode session list`, OPENCODE_DATA_DIR, or `--session /path/to/opencode.db --opencode-session-id ...`."
            )
        newest = global_newest_opencode_session()
        if newest:
            db_path, sid2 = newest
            return load_snapshot_from_opencode_sqlite(db_path, sid2, args.scope, args.model, args.provider)
        roots = ", ".join(str(p) for p in opencode_standard_dirs())
        raise SystemExit(
            f"No OpenCode SQLite (opencode*.db) found under: {roots}. "
            "Install sessions with OpenCode CLI, or set OPENCODE_DATA_DIR / XDG_DATA_HOME, or use manual token flags."
        )

    if agent_tool in MANUAL_ONLY_HOSTS:
        raise SystemExit(manual_mode_error(agent_tool))

    codex_path = newest_session_file()
    claude_path = newest_claude_transcript()
    opencode_ref = global_newest_opencode_session()

    sources = []
    if codex_path:
        sources.append(("codex", codex_path))
    if claude_path:
        sources.append(("claude-code", claude_path))
    if opencode_ref:
        sources.append(("opencode", opencode_ref))

    if len(sources) == 1:
        source_type, path = sources[0]
        if source_type == "codex":
            return load_snapshot_from_session(path, args.scope, args.model, args.provider)
        if source_type == "opencode":
            db_p, sid_o = path  # type: ignore[misc]
            return load_snapshot_from_opencode_sqlite(db_p, sid_o, args.scope, args.model, args.provider)
        return load_snapshot_from_claude_transcript(path, args.scope, args.model, args.provider)

    if len(sources) > 1:
        raise SystemExit(
            "Multiple software logs are available locally. "
            "Pass --agent-tool codex, --agent-tool claude-code, --agent-tool opencode, "
            "or run check-please inside the software whose conversation you want to bill. "
            "check-please does not guess across software."
        )

    raise SystemExit(
        "No Codex, Claude Code, or OpenCode session logs found locally. "
        "For Trae, automatic import is not implemented yet; provide --input-tokens and --output-tokens for manual mode."
    )


def load_pricing(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_price(pricing: Dict[str, Any], provider: str, model: str) -> Optional[Dict[str, Any]]:
    if not model or model == "UNRECORDED":
        return None
    provider_key = normalize(provider)
    model_key = normalize(model)
    for entry in pricing.get("models", []):
        entry_provider = normalize(str(entry.get("provider", "")))
        aliases = [entry.get("model", "")] + list(entry.get("aliases", []))
        alias_keys = {normalize(str(alias)) for alias in aliases}
        provider_matches = not provider_key or provider_key == "unknown" or provider_key == entry_provider
        if provider_matches and model_key in alias_keys:
            return entry
    for entry in pricing.get("models", []):
        aliases = [entry.get("model", "")] + list(entry.get("aliases", []))
        if model_key in {normalize(str(alias)) for alias in aliases}:
            return entry
    return None


def _priced_amount(
    entry: Dict[str, Any],
    input_tokens: int,
    cached_input_tokens: int,
    cache_write_tokens: int,
    output_tokens: int,
    reasoning_output_tokens: int,
) -> float:
    cached = min(cached_input_tokens, input_tokens)
    cache_write = min(cache_write_tokens, max(input_tokens - cached, 0))
    uncached = max(input_tokens - cached - cache_write, 0)

    input_rate = float(entry.get("input_per_million", 0.0))
    cached_rate = float(entry.get("cached_input_per_million", input_rate))
    cache_write_rate = float(entry.get("cache_write_5m_per_million", input_rate))
    output_rate = float(entry.get("output_per_million", 0.0))

    return (
        uncached * input_rate
        + cached * cached_rate
        + cache_write * cache_write_rate
        + (output_tokens + reasoning_output_tokens) * output_rate
    ) / 1_000_000


def estimate_cost(snapshot: UsageSnapshot, pricing_path: Path) -> PriceEstimate:
    # Sources that only record cumulative context tallies cannot be priced per token split.
    if snapshot.skip_price_estimate:
        return PriceEstimate(status="UNMAPPED", amount=None)

    pricing = load_pricing(pricing_path)
    currency = str(pricing.get("currency", "USD")).upper()

    if snapshot.model_breakdown:
        costs: list[ModelCost] = []
        totals: Dict[str, float] = {}
        mapped_entries = []
        for usage in snapshot.model_breakdown:
            entry = find_price(pricing, usage.provider, usage.model)
            if not entry:
                costs.append(ModelCost(model=usage.model, provider=usage.provider))
                continue
            entry_currency = str(entry.get("currency", currency)).upper()
            amount = _priced_amount(
                entry,
                usage.input_tokens,
                usage.cached_input_tokens,
                usage.cache_write_tokens,
                usage.output_tokens,
                usage.reasoning_output_tokens,
            )
            costs.append(
                ModelCost(
                    model=str(entry.get("model", usage.model)),
                    provider=usage.provider,
                    amount=amount,
                    currency=entry_currency,
                )
            )
            totals[entry_currency] = totals.get(entry_currency, 0.0) + amount
            mapped_entries.append(entry)
        if not mapped_entries:
            return PriceEstimate(status="UNMAPPED", amount=None, breakdown=tuple(costs))
        primary_currency = currency if currency in totals else max(totals, key=lambda key: totals[key])
        single = mapped_entries[0] if len(snapshot.model_breakdown) == 1 else None
        return PriceEstimate(
            status="ESTIMATE",
            amount=totals[primary_currency],
            model=str(single.get("model", snapshot.model)) if single else f"{len(snapshot.model_breakdown)} MODELS",
            currency=str(single.get("currency", primary_currency)).upper() if single else primary_currency,
            source_url=str(single.get("source_url", "")) if single else "",
            source_checked_at=str(single.get("source_checked_at", "")) if single else "",
            rate_note=str(single.get("rate_note", "")) if single else "",
            breakdown=tuple(costs),
        )

    entry = find_price(pricing, snapshot.provider, snapshot.model)
    if not entry:
        return PriceEstimate(status="UNMAPPED", amount=None)

    amount = _priced_amount(
        entry,
        snapshot.input_tokens,
        snapshot.cached_input_tokens,
        snapshot.cache_write_tokens,
        snapshot.output_tokens,
        snapshot.reasoning_output_tokens,
    )

    return PriceEstimate(
        status="ESTIMATE",
        amount=amount,
        model=str(entry.get("model", snapshot.model)),
        currency=str(entry.get("currency", currency)).upper(),
        source_url=str(entry.get("source_url", "")),
        source_checked_at=str(entry.get("source_checked_at", "")),
        rate_note=str(entry.get("rate_note", "")),
    )


def available_fields_report(snapshot: UsageSnapshot) -> Dict[str, Any]:
    available = sorted(snapshot.available_fields)
    rendered = [field for field in RECEIPT_TOKEN_FIELDS if field in snapshot.available_fields]
    unavailable_common = [field for field in COMMON_TOKEN_FIELDS if field not in snapshot.available_fields]
    available_optional = [field for field in OPTIONAL_TOKEN_FIELDS if field in snapshot.available_fields]
    report: Dict[str, Any] = {
        "source": snapshot.source,
        "scope": snapshot.scope,
        "provider": snapshot.provider,
        "model": snapshot.model,
        "token_usage_fields_available": available,
        "receipt_fields_common": list(COMMON_TOKEN_FIELDS),
        "receipt_fields_optional_if_available": list(OPTIONAL_TOKEN_FIELDS),
        "receipt_fields_rendered_by_default": rendered,
        "receipt_common_fields_missing_from_source": unavailable_common,
        "receipt_optional_fields_available": available_optional,
        "context_fields_available": ["model_context_window"] if snapshot.context_window else [],
        "metadata_fields_supported": [
            "session_id",
            "timestamp",
            "model_provider",
            "session_meta.model",
            "session_meta.model_id",
            "session_meta.model_name",
            "session_meta.model_slug",
            "turn_context.model",
        ],
        "known_unavailable_in_codex_token_count": [
            "cache_write_tokens unless provided manually or present in another provider log",
            "tool_use_tokens",
            "system_tokens",
        ],
    }
    if snapshot.skip_price_estimate:
        report["usd_estimate_note"] = "skipped: source only stores cumulative context token tallies"
    if snapshot.context_tokens is not None:
        report["context_snapshot_tokens_last_usage"] = snapshot.context_tokens
    return report
