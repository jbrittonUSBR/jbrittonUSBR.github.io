#!/usr/bin/env python3
"""Keep only NewsAPI articles that look like terrorism or U.S. critical-infrastructure hits.

Reads the JSON written by newspull_to_json.py and writes a same-shaped JSON
containing only matching articles.

Usage:
  python filter_ci_json.py --in newspull.json --out newspull_ci.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Title/citation must hit at least one of these (word-ish; case-insensitive).
KEEP = [
    r"\bcritical infrastructure\b",
    r"\bsubstations?\b",
    r"\btransformers?\b",
    r"\bpower grid\b",
    r"\belectric grid\b",
    r"\btransmission (line|tower|grid)\b",
    r"\bscada\b",
    r"\bindustrial control\b",
    r"\b\bics\b",
    r"\bplc\b",
    r"\bhydropower\b",
    r"\bhydroelectric\b",
    r"\bwater (utility|treatment|system|plant|infrastructure)\b",
    r"\bdam(s)?\b",
    r"\bpipeline\b",
    r"\brefiner(y|ies)\b",
    r"\bchemical plant\b",
    r"\bnuclear (plant|facility|site|power)\b",
    r"\bcbrn\b",
    r"\bsabotage\b",
    r"\bvandalism\b",
    r"\binsider threat\b",
    r"\bhostile surveillance\b",
    r"\bvehicle ramming\b",
    r"\bvehicle as a weapon\b",
    r"\bactive shooter\b",
    r"\bmass casualty\b",
    r"\bied\b",
    r"\bimprovised explosive\b",
    r"\bbombing\b",
    r"\bterroris(m|t|ts)\b",
    r"\bextremist(s| group)?\b",
    r"\bdve\b",
    r"\bfto\b",
    r"\bpatriot front\b",
    r"\bal[- ]?qaeda\b",
    r"\bal[- ]?shabaab\b",
    r"\bisis\b",
    r"\bespionage\b",
    r"\bcyber ?attack\b",
    r"\bransomware\b",
    r"\buas\b",
    r"\buav\b",
    r"\bdrone(s)?\b",
    r"\bairport\b",
    r"\bseaport\b",
    r"\brail(way|road)?\b",
    r"\bsubstation shooting\b",
    r"\bplot\b",
    r"\bthreat to\b",
]

# Transactional business copy — drop even if a KEEP term also appears.
TRANSACTIONAL = [
    r"\bcontract(s|ed|ing)?\b",
    r"\bawarded\b",
    r"\baward(s)?\b",
    r"\bwins? (a |the )?(contract|deal|award|bid|tender)\b",
    r"\bselected for\b",
    r"\bqualifies across\b",
    r"\bmarketplace\b",
    r"\bfranchise\b",
    r"\bloan to\b",
    r"\bcloses up to \$",
    r"\bmarket worth\b",
    r"\bstands? to benefit\b",
    r"\bstocks? stand to benefit\b",
    r"\bthese \d+ stocks\b",
    r"\bearnings call\b",
    r"\bquarterly dividend\b",
    r"\bpress release\b",
    r"\bmou with\b",
    r"\bsigns? (a )?(pact|deal|mou)\b",
    r"\braises €?\d",
    r"\bseries [a-d]\b",
    r"\bcapability streams\b",
    r"\bguidance\b",
    r"\bforecast\b",
    r"\bunlikely to meet\b",
    r"\bwon'?t meet\b",
    r"\bmiss(es|ed)? (its |the )?(20\d{2} )?(targets?|guidance|forecast)\b",
    r"\bbottom line\b",
    r"\bsales, profit\b",
    r"\bprofit forecast\b",
    r"\binvestor(s)? throughout\b",
]

# If these dominate and there is no strong CI/terror verb, drop.
NOISE = [
    r"\bmarket worth\b",
    r"\bstock\b",
    r"\bdividend\b",
    r"\bearnings\b",
    r"\binvestors?\b",
    r"\bnfl\b",
    r"\bnba\b",
    r"\bmlb\b",
    r"\bchiefs\b",
    r"\bboxing\b",
    r"\bguild wars\b",
    r"\bwildlife photos\b",
    r"\bpremier league\b",
    r"\bhollywood\b",
    r"\bbox office\b",
]

STRONG = [
    r"\bcritical infrastructure\b",
    r"\bsubstations?\b",
    r"\bscada\b",
    r"\bsabotage\b",
    r"\bterroris(m|t|ts)\b",
    r"\binsider threat\b",
    r"\bimprovised explosive\b",
    r"\bied\b",
    r"\bcyber ?attack\b",
    r"\bhostile surveillance\b",
    r"\bvehicle ramming\b",
    r"\bactive shooter\b",
    r"\bespionage\b",
    r"\bdam(s)?\b",
    r"\bhydropower\b",
    r"\bpower grid\b",
]


def haystack(article: dict) -> str:
    parts = [
        article.get("title") or "",
        article.get("citation") or "",
        article.get("outlet") or "",
        article.get("author") or "",
    ]
    return " ".join(parts)


def hits(patterns: list[str], text: str) -> list[str]:
    found = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            found.append(pat)
    return found


def is_match(article: dict) -> tuple[bool, list[str]]:
    text = haystack(article)
    if hits(TRANSACTIONAL, text):
        return False, []
    keep = hits(KEEP, text)
    if not keep:
        return False, []
    noise = hits(NOISE, text)
    strong = hits(STRONG, text)
    # Sports/markets only, no strong CI/terror term → drop
    if noise and not strong:
        return False, []
    return True, keep


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="src", required=True)
    parser.add_argument("--out", dest="dst", required=True)
    args = parser.parse_args()

    src = Path(args.src)
    data = json.loads(src.read_text(encoding="utf-8"))
    sections = data["results"] if isinstance(data, dict) and "results" in data else data
    if not isinstance(sections, list):
        raise SystemExit("Unexpected JSON shape")

    kept_sections = []
    kept_n = 0
    dropped_n = 0
    for section in sections:
        kept_arts = []
        for art in section.get("articles") or []:
            ok, reasons = is_match(art)
            if ok:
                row = dict(art)
                row["ci_match_patterns"] = reasons
                kept_arts.append(row)
                kept_n += 1
            else:
                dropped_n += 1
        kept_sections.append(
            {
                "query": section.get("query"),
                "count": len(kept_arts),
                "error": section.get("error"),
                "articles": kept_arts,
            }
        )

    out = {
        "pulled_at_utc": data.get("pulled_at_utc") if isinstance(data, dict) else None,
        "filtered_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filter": "terrorism_or_critical_infrastructure_keyword",
        "source_file": str(src),
        "article_count": kept_n,
        "dropped_count": dropped_n,
        "term_count": len(kept_sections),
        "results": kept_sections,
    }
    Path(args.dst).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Kept {kept_n}, dropped {dropped_n} -> {args.dst}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())