import urllib.parse
import feedparser
import requests

def build_google_news_rss_url(query: str, days: int, hl: str, gl: str, ceid: str) -> str:
    q = f"{query} when:{int(days)}d"
    return (
        "https://news.google.com/rss/search?"
        + "q=" + urllib.parse.quote(q)
        + f"&hl={urllib.parse.quote(hl)}&gl={urllib.parse.quote(gl)}&ceid={urllib.parse.quote(ceid)}"
    )

def fetch_news_rss(query: str, max_items: int = 8, days: int = 7, hl: str = "en-US", gl: str = "US", ceid: str = "US:en"):
    url = build_google_news_rss_url(query, days=days, hl=hl, gl=gl, ceid=ceid)
    r = requests.get(url, headers={"User-Agent": "stock-forecast-bot/1.0"}, timeout=30)
    r.raise_for_status()

    feed = feedparser.parse(r.text)
    items = []
    for e in feed.entries[:max_items]:
        items.append({
            "title": (e.get("title") or "").strip(),
            "link": (e.get("link") or "").strip(),
            "published": (e.get("published") or "").strip(),
            "source": (e.get("source", {}).get("title") if isinstance(e.get("source"), dict) else "") or ""
        })
    return items
