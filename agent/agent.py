import os
import json
import time
import random
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import anthropic

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SEARCH_QUERIES = [
    "PhD position fully funded 2026",
    "postdoctoral fellowship open call 2026",
    "call for papers academic journal 2026",
    "academic research grant application 2026",
    "international conference call for abstracts 2026",
    "PhD scholarship Africa 2026",
    "postdoc position Europe 2026",
    "research fellowship developing countries 2026",
    "open call papers humanities social science 2026",
    "STEM PhD fellowship fully funded 2026",
]

def google_search(query):
    """Search Google and return result links and snippets."""
    url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=5"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for g in soup.find_all("div", class_="tF2Cxc")[:5]:
            title_el = g.find("h3")
            link_el = g.find("a")
            snippet_el = g.find("div", class_="VwiC3b")
            if title_el and link_el:
                results.append({
                    "title": title_el.get_text(),
                    "link": link_el.get("href", ""),
                    "snippet": snippet_el.get_text() if snippet_el else ""
                })
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

def fetch_page_text(url):
    """Fetch and extract text from a URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:3000]
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return ""

def extract_with_claude(raw_text, source_url, query):
    """Use Claude to extract structured opportunity data."""
    prompt = f"""You are extracting academic opportunity listings from web content.

Source URL: {source_url}
Search query used: {query}

Raw content:
{raw_text}

Extract up to 3 academic opportunities from this content. For each one return a JSON array with objects containing these exact fields:
- type: one of "phd", "postdoc", "paper", "grant", "conf"
- title: clear concise title of the opportunity
- institution: university, organization, or journal name
- location: city and country if available, otherwise "Global"
- region: one of "africa", "europe", "north america", "asia", "global"
- field: academic discipline or field
- deadline: deadline date in YYYY-MM-DD format, or null if not found
- funding: funding details or null
- description: 1-2 sentence summary, maximum 200 characters
- link: the direct application or info URL

Rules:
- Only include real, specific opportunities with a clear title and institution
- Do not invent or guess any details
- If you cannot find a real opportunity, return an empty array []
- Return ONLY a valid JSON array, no explanation, no markdown

Example format:
[{{"type":"phd","title":"PhD in Climate Science","institution":"University of Ghana","location":"Accra, Ghana","region":"africa","field":"Climate Science","deadline":"2026-09-01","funding":"Fully funded","description":"3-year funded PhD on climate adaptation in West Africa.","link":"https://example.com"}}]"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"Claude error: {e}")
        return []

def get_existing_titles():
    """Fetch existing listing titles to avoid duplicates."""
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/listings?select=title&order=created_at.desc&limit=100",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            }
        )
        data = response.json()
        return set(item["title"].lower() for item in data)
    except Exception as e:
        print(f"Error fetching existing titles: {e}")
        return set()

def post_to_supabase(listing):
    """Post a single listing to Supabase."""
    payload = {
        "type": listing.get("type", "phd"),
        "title": listing.get("title", ""),
        "institution": listing.get("institution", ""),
        "location": listing.get("location", "Global"),
        "region": listing.get("region", "global"),
        "field": listing.get("field", ""),
        "deadline": listing.get("deadline"),
        "funding": listing.get("funding"),
        "description": listing.get("description", ""),
        "link": listing.get("link", ""),
        "source": "agent",
        "verified": False,
    }
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/listings",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json=payload
        )
        if response.status_code in [200, 201]:
            print(f"✅ Posted: {listing['title']}")
            return True
        else:
            print(f"❌ Failed to post {listing['title']}: {response.text}")
            return False
    except Exception as e:
        print(f"Post error: {e}")
        return False

def run_agent():
    print(f"\n🤖 Alaye Agent starting at {datetime.now(timezone.utc).isoformat()}")
    
    existing_titles = get_existing_titles()
    print(f"📋 Found {len(existing_titles)} existing listings")

    all_opportunities = []
    queries_to_use = random.sample(SEARCH_QUERIES, min(5, len(SEARCH_QUERIES)))

    for query in queries_to_use:
        print(f"\n🔍 Searching: {query}")
        results = google_search(query)
        print(f"   Found {len(results)} results")

        for result in results[:3]:
            url = result.get("link", "")
            if not url.startswith("http"):
                continue

            snippet = result.get("snippet", "") + " " + result.get("title", "")
            opportunities = extract_with_claude(snippet, url, query)

            if not opportunities:
                page_text = fetch_page_text(url)
                if page_text:
                    opportunities = extract_with_claude(page_text, url, query)

            for opp in opportunities:
                title = opp.get("title", "").strip()
                if not title or not opp.get("institution"):
                    continue
                if title.lower() in existing_titles:
                    print(f"   ⏭️  Duplicate skipped: {title}")
                    continue
                all_opportunities.append(opp)
                existing_titles.add(title.lower())

            time.sleep(2)

        time.sleep(3)

    print(f"\n📦 Total unique opportunities found: {len(all_opportunities)}")

    to_post = all_opportunities[:10]
    posted = 0

    for opp in to_post:
        if post_to_supabase(opp):
            posted += 1
        time.sleep(1)

    print(f"\n✅ Agent complete. Posted {posted} new listings.")

if __name__ == "__main__":
    print("🧪 Testing connections...")
    print(f"Supabase URL: {SUPABASE_URL[:30]}...")
    print(f"Anthropic key: {ANTHROPIC_API_KEY[:15]}...")
    existing = get_existing_titles()
    print(f"Supabase connection: {'✅ OK' if isinstance(existing, set) else '❌ Failed'}")
    run_agent()
