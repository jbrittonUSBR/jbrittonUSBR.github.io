#!/usr/bin/env python3
"""Keep only NewsAPI articles that look like terrorism or CI hits.

Title/citation screen aligned with the manual Grok filter:
tactical incident over strategy; drop transactional/Biztoc/market copy.

  python filter_ci_json.py --in newspull.json --out newspull_ci.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Tactical incident / designated-actor / CI-asset hits (title + citation).
# Bare nouns (drone, airport, rail, plot) are NOT enough by themselves.
KEEP = [
    r"\bcritical infrastructure\b",
    r"\bsubstations?\b",
    r"\btransformers?\b",
    r"\bpower grid\b",
    r"\belectric grid\b",
    r"\bhigh voltage\b",
    r"\btransmission (line|tower|grid)\b",
    r"\bscada\b",
    r"\bindustrial control\b",
    r"\bics advisory\b",
    r"\bplc\b",
    r"\bhydropower\b",
    r"\bhydroelectric\b",
    r"\bwater (utility|treatment|system|plant|infrastructure|distribution)\b",
    r"\bdam(s)?\b",
    r"\bpipeline\b",
    r"\brefiner(y|ies)\b",
    r"\bchemical plant\b",
    r"\bnuclear (plant|facility|site|power|safety)\b",
    r"\bundersea cable\b",
    r"\bfiber[- ]optic\b",
    r"\bsabotage\b",
    r"\bvandalism\b",
    r"\binsider threat\b",
    r"\bhostile surveillance\b",
    r"\bpre-?operational surveillance\b",
    r"\bvehicle ramming\b",
    r"\bvehicle as a weapon\b",
    r"\bdrove into a crowd\b",
    r"\bmowed down\b",
    r"\bactive shooter\b",
    r"\bmass (casualty|shooting)\b",
    r"\barmed (assault|hostile)\b",
    r"\bied\b",
    r"\bvbiied\b",
    r"\bimprovised explosive\b",
    r"\bbombing\b",
    r"\bcar bomb\b",
    r"\bsuicide bomb\b",
    r"\barson\b",
    r"\bcbrn\b",
    r"\bricin\b",
    r"\bdirty bomb\b",
    r"\bbioweapon\b",
    r"\bchemical weapon\b",
    r"\bterroris(m|t|ts)\b",
    r"\bfinance terrorism\b",
    r"\bmaterial support\b",
    r"\bmurder for hire\b",
    r"\bassassination\b",
    r"\bextremist(s| group)?\b",
    r"\bdve\b",
    r"\brmve\b",
    r"\bfto\b",
    r"\bpatriot front\b",
    r"\baccelerationist\b",
    r"\bal[- ]?qaeda\b",
    r"\bal[- ]?shabaab\b",
    r"\bisis\b",
    r"\bislamic state\b",
    r"\bhouthi(s)?\b",
    r"\birgc\b",
    r"\bquds force\b",
    r"\bespionage\b",
    r"\btrade secret\b",
    r"\bchargesheet\b",
    r"\brussian intelligence\b",
    r"\bchinese intelligence\b",
    r"\biranian intelligence\b",
    r"\bgru\b",
    r"\bfsb\b",
    r"\bsvr\b",
    r"\bministry of state security\b",
    r"\bmss\b",
    r"\bmois\b",
    r"\bvevak\b",
    r"\bcyber ?attack\b",
    r"\bransomware\b",
    r"\bsupply[- ]chain (compromise|breach|attack|poison)\b",
    r"\bsoftware supply\b",
    r"\bzero-?day\b",
    r"\bdrone (attack|strike|incursion|sighting)\b",
    r"\bhostile drone\b",
    r"\bcounter-?uas\b",
    r"\bkamikaze drone\b",
    r"\buas\b",
    r"\buav\b",
    r"\bsuspicious package\b",
    r"\bbomb squad\b",
    r"\bfoiled (plot|attack)\b",
    r"\b(charg(e|es|ed)|indictment|arrest(ed|s)?)\b.*\b(russian|china|chinese|iran|iranian)\b.*\b(plot|plots|assassination|murder)\b",
    r"\b(russian|china|chinese|iran|iranian)\b.*\b(charg(e|es|ed)|indictment)\b.*\b(plot|plots|assassination|murder)\b",
    r"\brussian plots?\b",
    r"\bassassination plots?\b",
]

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
    r"\bbetter drone stock\b",
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
    r"\bexclusive report by\b",
    r"\bworth \$\d",
]

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
    r"\breview:\b",
    r"\bthis story has been removed\b",
]

STRONG = [
    r"\bcritical infrastructure\b",
    r"\bsubstations?\b",
    r"\bscada\b",
    r"\bsabotage\b",
    r"\bterroris(m|t|ts)\b",
    r"\bfinance terrorism\b",
    r"\bmurder for hire\b",
    r"\bassassination\b",
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
    r"\bdrone (attack|strike|incursion)\b",
    r"\bhouthi",
    r"\bisis\b",
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
    title = (article.get("title") or "").strip()
    outlet = (article.get("outlet") or "").strip().lower()
    if not title or title.lower() in {"removed", "this story has been removed"}:
        return False, []
    if "biztoc" in outlet or "biztoc.com" in haystack(article).lower():
        return False, []
    text = haystack(article)
    if hits(TRANSACTIONAL, text):
        return False, []
    keep = hits(KEEP, text)
    if not keep:
        return False, []
    noise = hits(NOISE, text)
    strong = hits(STRONG, text)
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
        if not kept_arts:
            continue
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
        "accessed": data.get("accessed") if isinstance(data, dict) else None,
        "filtered_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filter": "manual_title_review_terrorism_or_CI",
        "source_file": src.name,
        "source_article_count": data.get("article_count") if isinstance(data, dict) else None,
        "article_count": kept_n,
        "dropped_count": dropped_n,
        "term_count": len(kept_sections),
        "note": "Title-only CI/terrorism screen. Transactional contract/award/market pieces excluded. Biztoc dropped.",
        "results": kept_sections,
    }
    Path(args.dst).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Kept {kept_n}, dropped {dropped_n} -> {args.dst}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
