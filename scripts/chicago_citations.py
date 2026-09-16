
#!/usr/bin/env python3
"""Write a Jekyll sources page in the exact 15 September bibliography format.

PowerShell:

  cd "C:\\Users\\JBritton\\OneDrive - DOI\\Desktop\\Agent"
  & "C:\\Users\\JBritton\\AppData\\Local\\anaconda3\\python.exe" ".\\chicago_citations.py" `
      --in ".\\newspull_ci.json" --out ".\\2026-09-16-sources.md"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_IN_NAMES = (
    "newspull_ci.json",
    "newspull_ci_mapped.json",
    "newspull.json",
)

HEADINGS = [
    ("drone or uas or uav", "UAS"),
    ("bombing or explosion or ied", "IED"),
    ("ballistic attack", "Ballistic Attack"),
    ("active shooter", "Armed Hostile Event"),
    ("vehicle ramming", "Vehicle Ramming"),
    ("arson", "Arson"),
    ("cbrn or chemical", "CBRN"),
    ("cyberattack or scada", "Cyber"),
    ("sabotage or vandalism or theft", "Sabotage, Vandalism, Theft (SVT)"),
    ("surveillance or", "Hostile Surveillance (HS)"),
    ("dve or", "Domestic Violent Extremism (DVE)"),
    ("terrorism or terrorist", "Terrorism"),
    ('"insider threat"', "Insider Threat"),
    ('"emerging threats"', "Emerging Threats"),
    ("neoluddite", "Data Centers"),
    ("pipeline or refinery", "Energy Attacks"),
    ("isis or", "Foreign Terrorist Organization (FTO)"),
    ("geopolitical or", "Geopolitical"),
    ("suspicious activity", "Suspicious Activity"),
    ("critical infrastructure", "Critical Infrastructure"),
    ("dams or hydropower", "Dams Sector"),
    ("espionage", "Espionage"),
    ("supply chain", "Supply Chain Issues"),
]


def heading_for(query: str) -> str:
    q = (query or "").lower()
    for needle, title in HEADINGS:
        if needle in q:
            return title
    return (query or "Other")[:60]


def angle_url(url: str) -> str:
    url = (url or "").strip().rstrip(".,;")
    url = url.replace("&amp;", "&")
    url = re.sub(r"^[<\[]+|[>\]]+$", "", url)
    if not url.startswith("http"):
        return url
    return f"<{url}>"


def chicago_cite(art: dict, accessed: str) -> str:
    cite = (art.get("citation") or "").strip()
    if cite:
        cite = re.sub(r"<?https?://[^\s<>]+>?", lambda m: angle_url(m.group(0)), cite)
        cite = cite.replace(">. Accessed", "> Accessed")
        if not cite.startswith("(U)"):
            cite = f"(U) {cite}"
        return cite
    author = art.get("author") or "Staff"
    title = art.get("title") or "No Title"
    outlet = art.get("outlet") or "Unknown"
    published = art.get("published") or "Recent"
    link = angle_url(art.get("link") or "")
    return (
        f'(U) {author}. "{title}." {outlet}, {published}. '
        f"{link} Accessed {accessed}."
    )


def resolve_input(given: str | None) -> Path:
    here = Path(__file__).resolve().parent
    cwd = Path.cwd()
    candidates: list[Path] = []
    if given:
        candidates.extend([Path(given), cwd / given, here / given])
    for name in DEFAULT_IN_NAMES:
        candidates.extend([cwd / name, here / name])
    for path in candidates:
        if path.is_file():
            return path
    tried = "\n  ".join(str(p) for p in candidates)
    raise SystemExit("JSON not found. Looked at:\n  " + tried)


def date_parts(data: dict) -> tuple[str, str, str, str]:
    pulled = data.get("pulled_at_utc") or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    day = str(pulled)[:10]
    y, m, d = day.split("-")
    pretty = datetime.strptime(day, "%Y-%m-%d").strftime("%d %B %Y").lstrip("0")
    return y, m, d, pretty


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("src", nargs="?", default="")
    parser.add_argument("dst", nargs="?", default="")
    parser.add_argument("--in", dest="src_opt", default="")
    parser.add_argument("--out", dest="dst_opt", default="")
    args = parser.parse_args()

    src = resolve_input(args.src_opt or args.src or None)
    data = json.loads(src.read_text(encoding="utf-8"))
    y, m, d, pretty = date_parts(data)
    accessed = data.get("accessed") or pretty

    dst_arg = args.dst_opt or args.dst
    if dst_arg:
        dst = Path(dst_arg)
        if not dst.is_absolute():
            dst = src.parent / dst
    else:
        dst = src.parent / f"{y}-{m}-{d}-sources.md"

    sections = data.get("results") if isinstance(data, dict) else data
    article_count = data.get("article_count")
    if article_count is None:
        article_count = sum(len(s.get("articles") or []) for s in sections or [])

    lines = [
        "---",
        "layout: page",
        f'title: "Sources — {pretty}"',
        f"permalink: /{y}/{m}/{d}/sources/",
        "---",
        f"- Accessed: {accessed}",
        f"- Pulled (UTC): {data.get('pulled_at_utc')}",
        f"- Filtered (UTC): {data.get('filtered_at_utc') or data.get('remapped_at_utc')}",
        f"- Source file: `{Path(str(data.get('source_file') or src.name)).name}`",
        f"- Source articles: {data.get('source_article_count') or ''}",
        f"- Filtered articles: {article_count}",
        f"- Query groups: {data.get('term_count') or len(sections or [])}",
        f"- Note: {data.get('note') or 'Title-only CI/terrorism screen. Transactional contract/award/market pieces excluded.'}",
    ]

    first = True
    for sec in sections or []:
        arts = sec.get("articles") or []
        if not arts:
            continue
        q = sec.get("query") or ""
        if first:
            first = False
        else:
            lines.append("---")
        lines.append(f"## {heading_for(q)}")
        lines.append(f"Querying NewsAPI for `{q}`...")
        lines.append(f"Articles found: {len(arts)}")
        for i, art in enumerate(arts, 1):
            lines.append(f"{i}. {chicago_cite(art, accessed)}")
    lines.append("---")
    lines.append("")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {dst}", file=sys.stderr)
    print(f"permalink /{y}/{m}/{d}/sources/  articles={article_count}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())