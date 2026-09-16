#!/usr/bin/env python3
"""Ask once for a NewsAPI key, run the watch-term queries, write JSON.

Usage:
  python newspull_to_json.py
  python newspull_to_json.py --out results.json
  python newspull_to_json.py --insecure --out results.json

The key is read from an initial prompt (or NEWSAPI_KEY if already set).
It is not written to disk.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

API_URL = "https://newsapi.org/v2/everything"
MAX_RESULTS = 20
REQUEST_PAUSE_SEC = 0.4

# Incident-first queries. NewsAPI /v2/everything: AND/OR/NOT and "phrases".
# Avoid bare nouns (Attack, Arson, Drone, Theft, water, ICS).
SEARCH_TERMS = [
    # needles "drone or uas or uav"
    '(Drone OR UAS OR UAV) AND ("drone attack" OR "drone strike" OR incursion OR "hostile drone" OR "counter-UAS" OR airport OR substation OR border OR port)',
    # needle "bombing or explosion or ied"
    '(Bombing OR explosion OR IED OR "improvised explosive device") AND (plot OR arrested OR detonat OR foiled OR blast OR VBIED)',
    # needle "ballistic attack"
    '"Ballistic attack" OR ((shooting OR sabotage OR attack) AND (transformer OR substation OR "power line" OR "high voltage"))',
    # needle "active shooter"
    '"Active shooter" OR "mass shooting" OR "mass casualty incident" OR "armed assault"',
    # needle "vehicle ramming"
    '"Vehicle ramming" OR "vehicle as a weapon" OR "drove into a crowd" OR "mowed down"',
    # needle "arson"
    'Arson AND (substation OR "power plant" OR mosque OR church OR synagogue OR warehouse OR rail OR electrical)',
    # needle "cbrn or chemical"
    '(CBRN OR chemical OR biological OR radiological OR nuclear) AND (weapon OR plot OR attack OR seized OR ricin OR "dirty bomb")',
    # needle "cyberattack or scada"
    '(Cyberattack OR SCADA OR "Industrial Control Systems") AND (hack OR ransomware OR breach OR sabotage OR outage OR "water utility" OR "power grid")',
    # needle "sabotage or vandalism or theft"
    '(Sabotage OR Vandalism OR Theft) AND (grid OR substation OR pipeline OR rail OR dam OR "power line" OR fiber OR copper)',
    # needle "surveillance or"
    'Surveillance AND ("pre-operational" OR dissident OR "murder for hire" OR substation OR airport OR dam OR "military base")',
    # FTO needle "dve or" — keep DVE OR at front
    'DVE OR "Patriot Front" OR RMVE OR accelerationist AND (plot OR arrest OR charged OR attack)',
    # needle "terrorism or terrorist"
    '(Terrorism OR terrorist OR "extremist group") AND (plot OR arrested OR charged OR foiled OR bombing) NOT memorial NOT anniversary',
    # needle "insider threat"
    '"Insider threat" OR ((employee OR contractor) AND (sabotage OR classified) AND (arrest OR charged))',
    # needle "emerging threats"
    '"Emerging threats" AND (infrastructure OR drone OR cyber OR terrorism OR "data center")',
    # needle neoluddite
    'Neoluddite OR "neo-Luddite" OR ("data center" AND (attack OR protest OR sabotage))',
    # energy / maritime (maps via remap: supply/attack → Cyber/FTO; keep explicit)
    '(pipeline OR refinery OR LNG OR tanker OR "oil port") AND (attack OR strike OR sabotage OR drone OR missile)',
    '(ISIS OR "Islamic State" OR "al-Qaeda" OR "al-Shabaab" OR Houthi OR Houthis) AND (attack OR plot OR claimed OR drone OR missile)',
    '("suspicious activity" OR "suspicious package") AND (airport OR station OR substation OR "federal building")',
    '"Critical infrastructure" AND (attack OR sabotage OR incident OR outage OR hack) NOT contract NOT loan',
    '(dams OR hydropower OR hydroelectric OR "water treatment" OR "water utility") AND (sabotage OR cyber OR attack OR threat)',
   '(Espionage OR "murder for hire" OR assassination OR "finance terrorism" OR "material support") AND (charged OR indictment OR arrested OR plot OR expelled OR diplomat OR "trade secret" OR classified)',
    '("Russian intelligence" OR GRU OR FSB OR SVR) AND (charged OR plot OR arrest OR sabotage OR surveillance)',
    '("Chinese intelligence" OR MSS OR "Ministry of State Security" OR Guoanbu OR MSSA OR "United Front" OR "PLA intelligence") AND (charged OR plot OR arrest OR sabotage OR surveillance OR espionage)',
    '("Iranian intelligence" OR MOIS OR VEVAK OR "IRGC" OR "Quds Force" OR Quds) AND (charged OR plot OR arrest OR sabotage OR surveillance OR assassination)',
    '("intelligence service" OR "intelligence services" OR "foreign intelligence" OR "state intelligence") AND (charged OR indictment OR plot OR arrest OR sabotage OR assassination OR "murder for hire")',
    '"Supply chain" AND (compromise OR breach OR poisoned OR "software supply")',
]


def request_api_key() -> str:
    existing = os.environ.get("NEWSAPI_KEY", "").strip()
    if existing and existing not in {"PASTE_KEY_HERE", "YOUR_KEY_HERE"}:
        return existing
    print("Enter your NewsAPI key (input is hidden):", file=sys.stderr)
    key = getpass.getpass("").strip()
    if not key:
        key = input("Key was empty; enter it visible this time: ").strip()
    if not key or key in {"PASTE_KEY_HERE", "YOUR_KEY_HERE"}:
        raise SystemExit("A real NewsAPI key is required.")
    return key


def ssl_verify(insecure: bool):
    if insecure or os.environ.get("NEWSAPI_SSL_VERIFY", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return False
    for name in ("NEWSAPI_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
        path = os.environ.get(name, "").strip().strip('"')
        if path:
            return path
    return True


def format_citation(article: dict, accessed_str: str) -> str:
    return (
        f"(U) {article['author']}. "
        f"\"{article['title']}.\" "
        f"{article['outlet']}, "
        f"{article['published']}. "
        f"{article['link']}. "
        f"Accessed {accessed_str}."
    )


def fetch_articles(keyword: str, api_key: str, verify, max_results: int = MAX_RESULTS) -> tuple[list[dict], str | None]:
    params = {
        "q": keyword,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": max_results,
        "apiKey": api_key,
    }
    try:
        response = requests.get(API_URL, params=params, timeout=20, verify=verify)
        data = response.json()
    except Exception as exc:
        msg = str(exc)
        if api_key:
            msg = msg.replace(api_key, "REDACTED")
        return [], msg

    if data.get("status") != "ok":
        return [], data.get("message", "Unknown NewsAPI error")

    articles = []
    for item in data.get("articles") or []:
        title = item.get("title") or "No Title"
        outlet = (item.get("source") or {}).get("name") or "Unknown Outlet"
        link = item.get("url") or "#"
        author = item.get("author")
        published_str = item.get("publishedAt")
        if not author or str(author).strip() == "":
            author = f"{outlet} Staff"
        try:
            dt = datetime.fromisoformat(str(published_str).replace("Z", "+00:00"))
            formatted_date = dt.strftime("%B %d, %Y").replace(" 0", " ")
        except Exception:
            formatted_date = "Recent"
        suffix = f" - {outlet}"
        if suffix in title:
            title = title[: title.rfind(suffix)].strip()
        articles.append(
            {
                "title": title,
                "link": link,
                "published": formatted_date,
                "publishedAt": published_str,
                "author": author,
                "outlet": outlet,
            }
        )
    return articles, None


def main() -> int:
    parser = argparse.ArgumentParser(description="NewsAPI pull to JSON")
    parser.add_argument(
        "--out",
        default="",
        help="JSON output path (default: newspull_YYYY-MM-DD.json in cwd)",
    )
    parser.add_argument(
        "--txt",
        default="",
        help="Citation text path (default: same name as JSON with .txt)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verify (DOI inspection workaround)",
    )
    args = parser.parse_args()

    if args.insecure:
        try:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

    api_key = request_api_key()
    verify = ssl_verify(args.insecure)
    accessed_str = datetime.now(timezone.utc).strftime("%B %d, %Y").replace(" 0", " ")
    pulled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sections = []
    text_chunks: list[str] = []
    total = 0
    for term in SEARCH_TERMS:
        print(f"Querying NewsAPI for '{term}'...", file=sys.stderr)
        articles, error = fetch_articles(term, api_key, verify)
        for art in articles:
            art["citation"] = format_citation(art, accessed_str)
        total += len(articles)
        print(f"Articles found: {len(articles)}", file=sys.stderr)
        if error:
            print(f"NewsAPI Error: {error}", file=sys.stderr)

        text_chunks.append(f"Querying NewsAPI for '{term}'...")
        text_chunks.append(f"Articles found: {len(articles)}")
        if error:
            text_chunks.append(f"NewsAPI Error: {error}")
        text_chunks.append(
            "=" * 20 + f" CITATION LIST FOR: {term.upper()} " + "=" * 20
        )
        if not articles:
            text_chunks.append("No articles found.")
        else:
            for idx, art in enumerate(articles, 1):
                text_chunks.append(f"{idx}. {art['citation']}")
        text_chunks.append("-" * 65)
        text_chunks.append("")

        sections.append(
            {
                "query": term,
                "count": len(articles),
                "error": error,
                "articles": [
                    {
                        "author": a["author"],
                        "title": a["title"],
                        "outlet": a["outlet"],
                        "published": a["published"],
                        "publishedAt": a["publishedAt"],
                        "link": a["link"],
                        "citation": a["citation"],
                    }
                    for a in articles
                ],
            }
        )
        time.sleep(REQUEST_PAUSE_SEC)

    payload = {
        "pulled_at_utc": pulled_at,
        "accessed": accessed_str,
        "page_size": MAX_RESULTS,
        "term_count": len(SEARCH_TERMS),
        "article_count": total,
        "results": sections,
    }

    out_path = args.out.strip() or f"newspull_{datetime.now().strftime('%Y-%m-%d')}.json"
    txt_path = args.txt.strip()
    if not txt_path:
        root, _ext = os.path.splitext(out_path)
        txt_path = root + ".txt"

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(text_chunks).rstrip() + "\n")

    print(f"Wrote {out_path} ({total} articles)", file=sys.stderr)
    print(f"Wrote {txt_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())