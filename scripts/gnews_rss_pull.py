#!/usr/bin/env python3
"""Google News RSS collector that emits the same JSON shape as newspull_to_json.py.

Uses SEARCH_TERMS from newspull_to_json.py in the same folder.

  python gnews_rss_pull.py --hours 48 --out newspull_gnews.json

Optional: pip install feedparser googlenewsdecoder newspaper3k beautifulsoup4
googlenewsdecoder is optional. Without it, links stay on news.google.com and
merge_newspull.py / filter should drop those.
"""

from __future__ import annotations

import argparse
import email.utils
import importlib.util
import json
import re
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse

socket.setdefaulttimeout(15)

try:
    import feedparser
except ImportError:
    raise SystemExit("pip install feedparser")

try:
    import requests
except ImportError:
    requests = None  # type: ignore

try:
    from googlenewsdecoder import gnewsdecoder
except Exception:
    gnewsdecoder = None  # type: ignore

B_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


def load_search_terms(script_dir: Path) -> list[str]:
    path = script_dir / "newspull_to_json.py"
    if not path.is_file():
        raise SystemExit(f"Cannot find {path} — put this script next to newspull_to_json.py")
    spec = importlib.util.spec_from_file_location("newspull_to_json", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    raw = list(getattr(mod, "SEARCH_TERMS"))
    terms: list[str] = []
    for t in raw:
        if isinstance(t, str) and t.strip():
            terms.append(t.strip())
        else:
            print(f"Skip non-string SEARCH_TERMS item: {t!r}", file=sys.stderr)
    return terms


def parse_rss_date(entry) -> datetime | None:
    raw = entry.get("published") or entry.get("updated")
    if not raw:
        return None
    tup = email.utils.parsedate_tz(raw)
    if not tup:
        return None
    ts = email.utils.mktime_tz(tup)
    return datetime.fromtimestamp(ts, timezone.utc)


def media_outlet(entry, url: str) -> str:
    src = entry.get("source")
    if src is not None and getattr(src, "title", None):
        return src.title
    host = urlparse(url).netloc.replace("www.", "")
    return host or "Unknown"


def resolve_google_url(google_url: str) -> str:
    if "news.google.com" not in google_url:
        return google_url
    if gnewsdecoder is not None:
        try:
            decoded = gnewsdecoder(google_url, interval=1)
            if decoded and decoded.get("status") and decoded.get("decoded_url"):
                return decoded["decoded_url"]
        except Exception:
            pass
    if requests is None:
        return google_url
    try:
        resp = requests.get(google_url, timeout=5, headers=B_HEADERS)
        match = re.search(r'URL=["\']?(https?://[^"\'>]+)', resp.text, re.IGNORECASE)
        if match:
            return match.group(1)
    except Exception:
        pass
    return google_url


def author_from_entry(entry) -> str | None:
    if entry.get("author") and str(entry.author).strip():
        return str(entry.author).strip()
    detail = entry.get("author_detail") or {}
    if isinstance(detail, dict) and detail.get("name"):
        return str(detail["name"]).strip()
    return None


def chicago(author: str, title: str, outlet: str, published: str, link: str, accessed: str) -> str:
    return (
        f'(U) {author}. "{title}." {outlet}, {published}. {link}. Accessed {accessed}.'
    )


def fetch_term(keyword: str, max_results: int, hours: int, sleep_s: float) -> list[dict]:
    q = quote_plus(keyword)
    rss_url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    print(f"Google News RSS: {keyword[:80]}...", file=sys.stderr)
    try:
        feed = feedparser.parse(rss_url)
    except Exception as exc:
        print(f"  RSS failed: {exc}", file=sys.stderr)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    accessed = datetime.now(timezone.utc).strftime("%B %d, %Y").replace(" 0", " ")
    articles: list[dict] = []

    for entry in feed.entries:
        published_dt = parse_rss_date(entry)
        if published_dt is None or published_dt < cutoff:
            continue
        google_url = entry.get("link") or ""
        title = (entry.get("title") or "").strip()
        if not title or not google_url:
            continue
        resolved = resolve_google_url(google_url)
        outlet = media_outlet(entry, resolved)
        if f" - {outlet}" in title:
            title = title[: title.rfind(f" - {outlet}")].strip()
        author = author_from_entry(entry) or f"{outlet} Staff"
        published = published_dt.strftime("%B %d, %Y").replace(" 0", " ")
        articles.append(
            {
                "author": author,
                "title": title,
                "outlet": outlet,
                "published": published,
                "publishedAt": published_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "link": resolved,
                "citation": chicago(author, title, outlet, published, resolved, accessed),
                "source": "gnews-rss",
            }
        )
        if len(articles) >= max_results:
            break
        if sleep_s:
            time.sleep(sleep_s)
    print(f"  {len(articles)} in window", file=sys.stderr)
    return articles


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="newspull_gnews.json")
    parser.add_argument("--hours", type=int, default=48)
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.4)
    parser.add_argument("--limit-terms", type=int, default=0, help="debug: first N terms only")
    args = parser.parse_args()

    terms = load_search_terms(here)
    if args.limit_terms:
        terms = terms[: args.limit_terms]

    now = datetime.now(timezone.utc)
    accessed = now.strftime("%B %d, %Y").replace(" 0", " ")
    results = []
    total = 0
    for term in terms:
        arts = fetch_term(term, args.max, args.hours, args.sleep)
        total += len(arts)
        results.append({"query": term, "count": len(arts), "error": None, "articles": arts})

    out = {
        "pulled_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "accessed": accessed,
        "page_size": args.max,
        "term_count": len(results),
        "article_count": total,
        "hours": args.hours,
        "collector": "gnews-rss",
        "results": results,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} articles={total} terms={len(results)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())