"""
Web Research Engine
- Wikipedia API (urllib, no external lib needed)
- DuckDuckGo Instant Answer API (free, no key needed)
- Google News RSS (free, no key needed)
- Keyword extraction for smart query building
"""

import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple
from collections import Counter


HEADERS = {
    "User-Agent": "FactChecker-Research/1.0 (educational fact-checking tool)",
    "Accept": "application/json, text/html",
}

REQUEST_TIMEOUT = 10


def safe_request(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """Make HTTP request, return response text or None on failure."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None


# ── Keyword Extractor ──────────────────────────────────────────────────────────
STOPWORDS = set("""
a about above after again against all also am an and any are as at be because
been before being below between both but by can cannot could did do does doing
don't down during each few for from further get got had has have having he her
here hers him his how i if in into is it its itself just let me more most my
myself no nor not of off on once only or other ought our own said same she
should so some such than that the their them then there these they this those
through to too under until up very was we were what when where which while
who will with would you your
""".split())

def extract_keywords(text: str, top_n: int = 6) -> List[str]:
    """Extract the most important keywords using TF + position weighting."""
    text_lower = text.lower()
    # Extract named entities (capitalized phrases)
    named_entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    
    # Word frequency
    words = re.findall(r'\b[a-z]{3,}\b', text_lower)
    freq = Counter(w for w in words if w not in STOPWORDS)
    
    # Score: frequency + named entity bonus
    keywords = []
    seen = set()
    
    # Named entities first
    for entity in named_entities:
        if entity.lower() not in STOPWORDS and entity not in seen and len(entity) > 3:
            keywords.append(entity)
            seen.add(entity.lower())
    
    # Top frequency words
    for word, count in freq.most_common(top_n * 2):
        if word not in seen and len(word) > 3:
            keywords.append(word)
            seen.add(word)
        if len(keywords) >= top_n + len(named_entities[:3]):
            break
    
    return keywords[:top_n]


def build_search_query(text: str, max_words: int = 6) -> str:
    """Build an optimized search query from input text."""
    keywords = extract_keywords(text, top_n=max_words)
    # Prioritize named entities + numbers
    numbers = re.findall(r'\b\d{4}\b|\b\d+(?:\.\d+)?\s*(?:percent|%|million|billion)\b', text[:500])
    
    query_parts = keywords[:5]
    if numbers:
        query_parts.append(numbers[0])
    
    return " ".join(query_parts[:6])


# ── Wikipedia Search ───────────────────────────────────────────────────────────
def wikipedia_search(query: str, sentences: int = 6) -> List[Dict]:
    """Search Wikipedia and return top article summaries."""
    results = []
    
    # Step 1: Get search results
    search_params = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": 3,
        "srprop": "snippet|titlesnippet"
    })
    url = f"https://en.wikipedia.org/w/api.php?{search_params}"
    raw = safe_request(url)
    
    if not raw:
        return results
    
    try:
        data = json.loads(raw)
        search_hits = data.get("query", {}).get("search", [])
    except Exception:
        return results
    
    # Step 2: Fetch extract for each result
    for hit in search_hits[:3]:
        title = hit.get("title", "")
        if not title:
            continue
        
        extract_params = urllib.parse.urlencode({
            "action": "query",
            "format": "json",
            "prop": "extracts|info",
            "exintro": True,
            "explaintext": True,
            "exsentences": sentences,
            "redirects": 1,
            "inprop": "url",
            "titles": title
        })
        ext_url = f"https://en.wikipedia.org/w/api.php?{extract_params}"
        ext_raw = safe_request(ext_url)
        
        if not ext_raw:
            continue
        
        try:
            ext_data = json.loads(ext_raw)
            pages = ext_data.get("query", {}).get("pages", {})
            page = next(iter(pages.values()))
            extract = page.get("extract", "")
            page_url = page.get("fullurl", f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}")
            
            if extract and len(extract) > 100:
                results.append({
                    "title": title,
                    "text": extract,
                    "snippet": extract[:300],
                    "url": page_url,
                    "type": "wikipedia",
                    "source_name": "Wikipedia"
                })
        except Exception:
            continue
        
        time.sleep(0.15)  # polite delay
    
    return results


# ── DuckDuckGo Instant Answer API ─────────────────────────────────────────────
def duckduckgo_instant(query: str) -> Optional[Dict]:
    """Query DuckDuckGo's free Instant Answer API."""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1
    })
    url = f"https://api.duckduckgo.com/?{params}"
    raw = safe_request(url)
    
    if not raw:
        return None
    
    try:
        data = json.loads(raw)
        abstract = data.get("AbstractText", "")
        abstract_url = data.get("AbstractURL", "")
        abstract_source = data.get("AbstractSource", "")
        
        related = []
        for item in data.get("RelatedTopics", [])[:4]:
            if isinstance(item, dict) and item.get("Text"):
                related.append({
                    "text": item["Text"],
                    "url": item.get("FirstURL", "")
                })
        
        if abstract or related:
            return {
                "abstract": abstract,
                "url": abstract_url,
                "source": abstract_source,
                "related": related
            }
    except Exception:
        pass
    
    return None


# ── Google News RSS (free, no API key) ────────────────────────────────────────
def google_news_search(query: str, max_results: int = 5) -> List[Dict]:
    """Fetch recent news via Google News RSS feed."""
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"
    raw = safe_request(url)
    
    if not raw:
        return []
    
    results = []
    try:
        root = ET.fromstring(raw)
        channel = root.find("channel")
        if not channel:
            return []
        
        for item in channel.findall("item")[:max_results]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            
            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""
            desc = desc_el.text if desc_el is not None else ""
            pub_date = pub_el.text if pub_el is not None else ""
            
            # Clean HTML from description
            desc = re.sub(r'<[^>]+>', '', desc or "").strip()
            
            if title:
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": desc[:300],
                    "text": desc,
                    "pub_date": pub_date[:16] if pub_date else "",
                    "type": "news",
                    "source_name": _extract_source_name(title)
                })
    except Exception:
        pass
    
    return results


def _extract_source_name(title: str) -> str:
    """Extract source name from Google News title format 'Headline - Source'."""
    parts = title.rsplit(" - ", 1)
    return parts[-1].strip() if len(parts) > 1 else "News"


# ── Main Research Function ─────────────────────────────────────────────────────
def research_claim(text: str, query_override: str = None) -> Dict:
    """
    Full research pipeline:
    1. Extract keywords → build query
    2. Wikipedia search
    3. DuckDuckGo instant answer
    4. Google News RSS
    Returns structured results for analysis.
    """
    query = query_override or build_search_query(text)
    
    results = {
        "query_used": query,
        "keywords": extract_keywords(text),
        "wikipedia": [],
        "news": [],
        "ddg_instant": None,
        "all_sources": [],
        "total_sources": 0,
        "raw_text_corpus": ""
    }
    
    # Wikipedia
    wiki_results = wikipedia_search(query, sentences=7)
    results["wikipedia"] = wiki_results
    
    # DuckDuckGo
    ddg = duckduckgo_instant(query)
    results["ddg_instant"] = ddg
    
    # Google News
    news_results = google_news_search(query, max_results=5)
    results["news"] = news_results
    
    # Combine all sources
    all_sources = []
    for w in wiki_results:
        all_sources.append(w)
    for n in news_results:
        all_sources.append(n)
    if ddg and ddg.get("abstract"):
        all_sources.append({
            "title": f"DuckDuckGo: {ddg.get('source', 'Reference')}",
            "text": ddg["abstract"],
            "snippet": ddg["abstract"][:300],
            "url": ddg.get("url", ""),
            "type": "reference",
            "source_name": ddg.get("source", "Reference")
        })
    
    results["all_sources"] = all_sources
    results["total_sources"] = len(all_sources)
    
    # Build raw corpus for NLP
    corpus_parts = []
    for src in all_sources:
        corpus_parts.append(src.get("text", "") or src.get("snippet", ""))
    results["raw_text_corpus"] = " ".join(corpus_parts)
    
    return results
