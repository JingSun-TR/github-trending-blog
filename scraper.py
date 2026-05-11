#!/usr/bin/env python3
"""
GitHub Trending Scraper

Fetches https://github.com/trending and extracts repository data:
- name, owner, description, language, stars, forks, today's stars, URL

Outputs JSON to data/trending-YYYY-MM-DD.json
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

TRENDING_URL = "https://github.com/trending?since=daily"
DATA_DIR = Path(__file__).parent / "data"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _parse_number(text: str) -> int:
    """Parse '1,234' or '1.2k' into an integer."""
    text = text.strip().lower()
    if "k" in text:
        num = float(text.replace("k", "").replace(",", ""))
        return int(num * 1000)
    return int(text.replace(",", ""))


def fetch_trending(timeout: int = 30) -> list[dict]:
    """Scrape GitHub trending and return a list of repo dicts."""
    print(f"Fetching {TRENDING_URL} ...")
    resp = httpx.get(TRENDING_URL, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    repos = []
    # Each trending repo is an <article> with class Box-row
    articles = soup.find_all("article", class_="Box-row")
    if not articles:
        # Fallback: GitHub sometimes changes class names
        articles = soup.select('[class*="Box-row"]')
        print(f"  Warning: primary selector failed, fallback found {len(articles)} elements")

    for article in articles:
        try:
            # --- Repo name & owner ---
            h2 = article.find("h2")
            if not h2:
                continue
            link = h2.find("a")
            if not link:
                continue
            href = link.get("href", "").strip()
            # href looks like "/owner/name"
            parts = href.strip("/").split("/")
            if len(parts) < 2:
                continue
            owner, name = parts[0], parts[1]

            # --- Description ---
            desc_p = article.find("p")
            description = desc_p.get_text(strip=True) if desc_p else ""

            # --- Language ---
            lang_el = article.find("span", itemprop="programmingLanguage")
            language = lang_el.get_text(strip=True) if lang_el else "Unknown"

            # --- Stars, forks, today's stars ---
            # Links with star/fork icons that contain the numbers
            stats_links = article.find_all("a", class_=re.compile(r"Link--muted"))
            stars_total = 0
            forks_total = 0
            stars_today = 0

            for slink in stats_links:
                text = slink.get_text(strip=True)
                href_link = slink.get("href", "")
                # href contains /stargazers or /forks
                if "/stargazers" in href_link:
                    stars_total = _parse_number(text)
                elif "/forks" in href_link:
                    forks_total = _parse_number(text)

            # Today's stars are often in a span like "123 stars today"
            today_span = article.find("span", class_=re.compile(r"d-inline-block"))
            if today_span:
                today_text = today_span.get_text(strip=True)
                match = re.search(r"([\d,]+)\s*stars?\s*today", today_text, re.IGNORECASE)
                if match:
                    stars_today = _parse_number(match.group(1))
            if not stars_today:
                # Alternative: look for text with "stars today" anywhere in the article
                art_text = article.get_text()
                match = re.search(r"([\d,]+)\s*stars?\s*today", art_text, re.IGNORECASE)
                if match:
                    stars_today = _parse_number(match.group(1))

            repos.append({
                "owner": owner,
                "name": name,
                "full_name": f"{owner}/{name}",
                "url": f"https://github.com/{owner}/{name}",
                "description": description,
                "language": language,
                "stars": stars_total,
                "forks": forks_total,
                "stars_today": stars_today,
            })
        except Exception as e:
            print(f"  Skipping one repo — parse error: {e}", file=sys.stderr)
            continue

    print(f"  Found {len(repos)} trending repositories")
    return repos


def save(repos: list[dict], target_date: str | None = None):
    """Save repo list as JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if target_date is None:
        target_date = date.today().isoformat()
    path = DATA_DIR / f"trending-{target_date}.json"
    doc = {
        "date": target_date,
        "source": "https://github.com/trending?since=daily",
        "count": len(repos),
        "repositories": repos,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
    print(f"Saved to {path}")
    return path


def main():
    today = date.today().isoformat()
    try:
        repos = fetch_trending()
    except Exception as e:
        print(f"Error fetching trending: {e}", file=sys.stderr)
        sys.exit(1)

    if not repos:
        print("No repositories found — GitHub may have changed its HTML structure.", file=sys.stderr)
        sys.exit(1)

    save(repos, today)


if __name__ == "__main__":
    main()
