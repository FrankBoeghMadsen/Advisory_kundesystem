from datetime import datetime
import hashlib
import feedparser
import requests
from bs4 import BeautifulSoup

def make_key(url, title):
    return hashlib.sha256((url + "|" + title).encode("utf-8")).hexdigest()

def fetch_rss(source):
    feed = feedparser.parse(source["url"])
    items = []
    for entry in feed.entries[:50]:
        items.append({
            "source_id": source["id"],
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "published_at": entry.get("published", entry.get("updated", "")),
            "raw_summary": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True),
            "collected_at": datetime.utcnow().isoformat(),
            "unique_key": make_key(entry.get("link", ""), entry.get("title", ""))
        })
    return items

def fetch_web_page(source):
    # Simple, polite single-page fetch for public pages configured by user.
    headers = {"User-Agent": "FrankAdvisoryMonitor/1.0 (+passive monitoring; contact: local user)"}
    r = requests.get(source["url"], headers=headers, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else source["url"]
    text = soup.get_text(" ", strip=True)[:3000]
    return [{
        "source_id": source["id"],
        "title": title,
        "url": source["url"],
        "published_at": "",
        "raw_summary": text,
        "collected_at": datetime.utcnow().isoformat(),
        "unique_key": make_key(source["url"], title + text[:200])
    }]

def fetch_source(source):
    if source["source_type"] == "rss":
        return fetch_rss(source)
    if source["source_type"] == "web":
        return fetch_web_page(source)
    return []

def extract_context_from_url(url, search_terms):
    """Best-effort extraction of a relevant excerpt from a source page."""
    if not url:
        return {"excerpt": "", "matched_terms": ""}
    try:
        headers = {"User-Agent": "FrankAdvisoryMonitor/2.1 (+passive monitoring; local user)"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ", strip=True).split())
        lower = text.lower()
        matches = []
        positions = []
        for term in search_terms:
            term = (term or "").strip()
            if len(term) < 3:
                continue
            idx = lower.find(term.lower())
            if idx >= 0:
                matches.append(term)
                positions.append(idx)
        if not positions:
            return {"excerpt": text[:1200], "matched_terms": ""}
        start = max(min(positions) - 350, 0)
        end = min(max(positions) + 850, len(text))
        return {"excerpt": text[start:end], "matched_terms": " | ".join(dict.fromkeys(matches))}
    except Exception:
        return {"excerpt": "", "matched_terms": ""}
