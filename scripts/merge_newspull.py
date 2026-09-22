#!/usr/bin/env python3
"""Merge two newspull JSON files (NewsAPI + Google RSS) into one.

Same query strings are concatenated then deduped by normalized URL.
Unresolved news.google.com links are dropped.

  python merge_newspull.py --a newspull.json --b newspull_gnews.json --out newspull_merged.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def norm_url(url: str) -> str:
    u = (url or "").strip().replace("&amp;", "&")
    p = urlparse(u)
    host = (p.netloc or "").lower().removeprefix("www.")
    path = (p.path or "").rstrip("/")
    return urlunparse(("", host, path, "", "", "")).lower()


def is_google_wrapper(url: str) -> bool:
    host = urlparse(url.replace("&amp;", "&")).netloc.lower()
    return "news.google.com" in host


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "results" not in data:
        raise SystemExit(f"Unexpected shape: {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True, help="NewsAPI newspull.json")
    parser.add_argument("--b", required=True, help="gnews newspull_gnews.json")
    parser.add_argument("--out", default="newspull_merged.json")
    args = parser.parse_args()

    a = load(Path(args.a))
    b = load(Path(args.b))

    by_query: dict[str, list[dict]] = {}
    order: list[str] = []
    for src in (a, b):
        for sec in src.get("results") or []:
            q = sec.get("query") or ""
            if q not in by_query:
                by_query[q] = []
                order.append(q)
            by_query[q].extend(sec.get("articles") or [])

    results = []
    kept = dropped = 0
    for q in order:
        seen: set[str] = set()
        arts = []
        for art in by_query[q]:
            link = art.get("link") or ""
            if is_google_wrapper(link):
                dropped += 1
                continue
            key = norm_url(link) or (art.get("title") or "").strip().lower()
            if not key or key in seen:
                dropped += 1
                continue
            seen.add(key)
            arts.append(art)
            kept += 1
        if arts:
            results.append({"query": q, "count": len(arts), "error": None, "articles": arts})

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {
        "pulled_at_utc": a.get("pulled_at_utc") or now,
        "accessed": a.get("accessed") or b.get("accessed"),
        "merged_at_utc": now,
        "page_size": max(int(a.get("page_size") or 0), int(b.get("page_size") or 0)),
        "term_count": len(results),
        "article_count": kept,
        "dropped_dupes_or_google": dropped,
        "sources": [str(args.a), str(args.b)],
        "results": results,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} kept={kept} dropped={dropped} sections={len(results)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())