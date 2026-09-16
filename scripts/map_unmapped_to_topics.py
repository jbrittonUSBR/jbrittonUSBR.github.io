#!/usr/bin/env python3
"""Assign articles to TOPIC_MAP folders. Title beats query.

Usage:
  python map_unmapped_to_topics.py --in newspull_ci.json --out newspull_ci_mapped.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

TOPIC_MAP = [
    ("drone or uas or uav", ("1 - UAS", "UAS")),
    ("bombing or explosion or ied", ("2 - IED", "IED")),
    ("ballistic attack", ("3 - Ballistic", "Ballistic")),
    ("active shooter", ("4 - Armed Hostile Event (AHE)", "AHE")),
    ("vehicle ramming", ("5 - Vehicle Ramming Incident (VRI)", "VRI")),
    ("arson", ("6 - Arson", "Arson")),
    ("cbrn or chemical", ("7 - CBRN", "CBRN")),
    ("cyberattack or scada", ("8 - Cyber", "Cyber")),
    ("sabotage or vandalism or theft", ("9 - Sabotage, Vandalism, Theft", "SVT")),
    ("surveillance or", ("10 - Hostile Surveillance (HS)", "HS")),
    ('"emerging threats"', ("11 - Emerging Trends", "ET")),
    ("dve or", ("12 - DVE", "DVE")),
    ("terrorism or terrorist", ("13 - FTO", "FTO")),
    ("geopolitical or", ("14 - NST", "NST")),
    ('"insider threat"', ("15 - Insider Threat", "Insider")),
    ("russian intelligence", ("15 - Insider Threat", "Insider")),
    ("chinese intelligence", ("15 - Insider Threat", "Insider")),
    ("iranian intelligence", ("15 - Insider Threat", "Insider")),
    ("intelligence service", ("15 - Insider Threat", "Insider")),
    ("neoluddite", ("16 - Grievance Triggers", "GT")),
]

CANONICAL_QUERY = {
    "UAS": "Drone OR UAS OR UAV",
    "IED": 'Bombing OR explosion OR IED OR "improvised explosive device"',
    "Ballistic": '"Ballistic attack" OR (shooting AND transformer) OR (shooting AND substation)',
    "AHE": '"Active shooter" OR (shooting AND "mass casualty") OR "mass casualty"',
    "VRI": '"Vehicle ramming" OR "vehicle as a weapon" OR "vehicle attack"',
    "ARN": "Arson",
    "CBRN": "CBRN OR chemical OR biological OR radiological OR nuclear",
    "Cyber": 'Cyberattack OR SCADA OR "Industrial Control Systems" OR ICS OR (dams AND sabotage) OR PLC',
    "SVT": "Sabotage OR Vandalism OR Theft",
    "HS": 'Surveillance OR "Hostile surveillance"',
    "ET": '"Emerging threats"',
    "DVE": 'DVE OR "far-right" OR "Patriot Front"',
    "FTO": 'Terrorism OR terrorist OR "extremist group"',
    "NST": 'Geopolitical OR "international issues"',
    "Insider": '"Insider threat"',
    "GT": 'Neoluddite OR "neo-Luddite"',
}

# Title-only overrides. First match wins. Checked BEFORE query mapping
# so a blast under "suspicious activity" does not land in Cyber.
TITLE_OVERRIDE = [
    (r"\b(ied|vbiied|car bomb|suicide bomb|bomb plot|weapons depot|ammo depot|arms depot)\b", "IED"),
    (r"\b(explosion|blast|detonat)\b.*(train|station|airport|subway|metro|mosque|market|depot)", "IED"),
    (r"(train|station|airport|subway|metro).*\b(explosion|blast|bomb)\b", "IED"),
    (r"\bramming\b|\bute\b|drove into a crowd|mowed down|vehicle as a weapon", "VRI"),
    (r"\b(active shooter|mass shooting|mass casualty|armed assault)\b", "AHE"),
    (r"\b(drone strike|drone attack|hostile drone|counter-?uas|c-uas|uav strike)\b", "UAS"),
    (r"\b(power grid|substation|high voltage|transformer|power line).*\b(sabotage|arrest|attack|fire|device)", "SVT"),
    (r"\b(sabotage|substation fire|trackside fire)\b", "SVT"),
    (r"\b(ransomware|scada|industrial control|water utility|phishing|zero-day|infostealer)\b", "Cyber"),
    (r"\b(espionage|trade.secret|classified|spying|chargesheet)\b", "Insider"),
    (r"\b(isis|islamic state|al-?qaeda|al-?shabaab|houthi|patriot front|neo-nazi)\b", "FTO"),
    (r"\bterroris", "FTO"),
    (r"data center", "ET"),
]

REMAP_RULES = TITLE_OVERRIDE + [
    (r"synagogue|palestine action", "FTO"),
    (r"airport drone|drone attack on german airport", "UAS"),
    (r"hybrid attacks on germany", "SVT"),
]

STOP = {
    "a", "an", "the", "of", "and", "or", "to", "in", "on", "for", "after",
    "as", "at", "by", "from", "with", "over", "into", "is", "are", "was",
    "video", "report", "exclusive", "update", "says", "say", "accused",
}


def topic_for_query(query: str):
    q = (query or "").strip().lower()
    for needle, dest in TOPIC_MAP:
        if needle in q:
            return dest
    return None


def folder_for_prefix(prefix: str) -> str:
    return next(f for n, (f, p) in TOPIC_MAP if p == prefix)


def title_fingerprint(title: str) -> str:
    t = (title or "").lower().replace("’", "'")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    words = [w for w in t.split() if w not in STOP and len(w) > 2]
    return " ".join(words[:10])


def titles_same_story(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    wa, wb = set(a.split()), set(b.split())
    if wa and wb:
        overlap = len(wa & wb)
        if overlap >= 4 and overlap / max(len(wa), len(wb)) >= 0.45:
            return True
    return SequenceMatcher(None, a, b).ratio() >= 0.82


def assign(article: dict, original_query: str) -> tuple[str, str, str, bool]:
    """Return folder, prefix, dest_query, overridden."""
    title = article.get("title") or ""
    citation = article.get("citation") or ""
    blob = f"{title} {citation}"
    for pat, prefix in TITLE_OVERRIDE:
        if re.search(pat, blob, flags=re.IGNORECASE):
            return folder_for_prefix(prefix), prefix, CANONICAL_QUERY[prefix], True
    mapped = topic_for_query(original_query)
    if mapped:
        folder, prefix = mapped
        return folder, prefix, original_query, False
    qblob = f"{original_query} {blob}"
    for pat, prefix in REMAP_RULES:
        if re.search(pat, qblob, flags=re.IGNORECASE):
            return folder_for_prefix(prefix), prefix, CANONICAL_QUERY[prefix], True
    q = (original_query or "").lower()
    if "espionage" in q:
        return "15 - Insider Threat", "Insider", CANONICAL_QUERY["Insider"], True
    if "supply chain" in q:
        return "8 - Cyber", "Cyber", CANONICAL_QUERY["Cyber"], True
    if "suspicious activity" in q:
        return "13 - FTO", "FTO", CANONICAL_QUERY["FTO"], True
    if "critical infrastructure" in q:
        return "9 - Sabotage, Vandalism, Theft", "SVT", CANONICAL_QUERY["SVT"], True
    if "dams or hydropower" in q or "water treatment" in q or "water utility" in q:
        return "8 - Cyber", "Cyber", CANONICAL_QUERY["Cyber"], True
    if re.fullmatch(r"\s*attack\s*", q):
        return "13 - FTO", "FTO", CANONICAL_QUERY["FTO"], True
    return "8 - Cyber", "Cyber", CANONICAL_QUERY["Cyber"], True


def resolve_input(given: str | None) -> Path:
    script_dir = Path(__file__).resolve().parent
    candidates = []
    if given:
        candidates.append(Path(given))
        candidates.append(script_dir / given)
    candidates.extend(
        [
            Path.cwd() / "newspull_ci.json",
            script_dir / "newspull_ci.json",
            Path.cwd() / "newspull.json",
            script_dir / "newspull.json",
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    tried = "\n  ".join(str(p) for p in candidates)
    raise SystemExit("JSON not found. Looked at:\n  " + tried)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="src", default="")
    parser.add_argument("--out", dest="dst", default="")
    args = parser.parse_args()

    src = resolve_input(args.src or None)
    dst = Path(args.dst) if args.dst else src.with_name("newspull_ci_mapped.json")
    if not dst.is_absolute():
        dst = src.parent / dst.name

    print(f"Reading {src}", file=sys.stderr)
    data = json.loads(src.read_text(encoding="utf-8"))
    sections = data["results"] if isinstance(data, dict) else data

    buckets: dict[str, dict] = {}
    remapped_n = passthrough_n = dropped_dupes = 0
    seen_urls: set[str] = set()
    seen_fps: list[str] = []

    def norm_url(url: str) -> str:
        return (url or "").strip().replace("&amp;", "&").split("#", 1)[0].rstrip("/").lower()

    for section in sections:
        query = section.get("query") or ""
        for article in section.get("articles") or []:
            url = norm_url(article.get("link") or "")
            fp = title_fingerprint(article.get("title") or "")
            if url and url in seen_urls:
                dropped_dupes += 1
                continue
            if fp and any(titles_same_story(fp, old) for old in seen_fps):
                dropped_dupes += 1
                continue
            if url:
                seen_urls.add(url)
            if fp:
                seen_fps.append(fp)

            folder, prefix, dest_query, overridden = assign(article, query)
            row = dict(article)
            if overridden:
                row["original_query"] = query
                row["remapped_to"] = f"{folder} / {prefix}"
                remapped_n += 1
            else:
                passthrough_n += 1
            if dest_query not in buckets:
                buckets[dest_query] = {
                    "query": dest_query,
                    "count": 0,
                    "error": None,
                    "articles": [],
                }
            buckets[dest_query]["articles"].append(row)
            buckets[dest_query]["count"] += 1

    out = {
        "pulled_at_utc": data.get("pulled_at_utc") if isinstance(data, dict) else None,
        "accessed": data.get("accessed") if isinstance(data, dict) else None,
        "remapped_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": str(src),
        "passthrough_count": passthrough_n,
        "remapped_count": remapped_n,
        "dropped_duplicate_urls": dropped_dupes,
        "article_count": passthrough_n + remapped_n,
        "term_count": len(buckets),
        "results": list(buckets.values()),
    }
    dst.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"passthrough={passthrough_n} remapped={remapped_n} "
        f"dropped_dupes={dropped_dupes} -> {dst}",
        file=sys.stderr,
    )
    for section in out["results"]:
        extra = [a for a in section["articles"] if a.get("original_query")]
        if extra:
            print(f"  {section['query']}:", file=sys.stderr)
            for a in extra:
                print(f"    [{a['remapped_to']}] {a['title'][:90]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())