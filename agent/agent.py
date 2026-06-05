import os
import json
import time
import random
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import anthropic
import xml.etree.ElementTree as ET

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

FREE_SOURCES = [
    {
        "name": "EURAXESS RSS",
        "url": "https://euraxess.ec.europa.eu/jobs/feed",
        "type": "rss"
    },
    {
        "name": "ReliefWeb Grants RSS",
        "url": "https://reliefweb.int/updates/rss.xml?search=academic+grant+fellowship",
        "type": "rss"
    },
    {
        "name": "Scholarshipdb PhD",
        "url": "https://scholarshipdb.net/scholarships",
        "type": "html"
    },
    {
        "name": "CFP List",
        "url": "https://cfplist.com/",
        "type": "html"
    },
    {
        "name": "Academic Positions",
        "url": "https://academicpositions.com/jobs",
        "type": "html"
    },
    {
        "name": "Grants.gov RSS",
        "url": "https://www.grants.gov/rss/GG_NewOppByCategory.xml",
        "type": "rss"
    },
    {
        "name": "Research Professional News",
        "url": "https://www.researchprofessionalnews.com/rn-funding-insight-2026/",
        "type": "html"
    },
    {
        "name": "FindAPhD",
        "url": "https://www.findaphd.com/phds/?Keywords=funded",
        "type": "html"
    },
]

def fetch_rss(url):
    """Fetch and parse RSS feed."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        root = ET.fromstring(response.content)
        items = []
        for item in root.iter("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "text": f"{title}. {description[:500]}. Published: {pub_date}"
                })
        print(f"   RSS: found {len(items)} items")
        return items[:8]
    except Exception as e:
        print(f"   RSS error: {e}")
        return []

def fetch_html(url):
    """Fetch HTML page and extract text."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        print(f"   HTML: fetched {len(text)} chars")
        return [{"title": url, "link": url, "text": text[:4000]}]
    except Exception as e:
        print(f"   HTML error: {e}")
        return []

def extract_with_claude(items, source_name):
    """Use Claude to extract structured opportunity data from items."""
    if not items:
        return []

    combined = ""
    for i, item in enumerate(items[:6]):
        combined += f"\n--- Item {i+1} ---\n"
        combined += f"Title: {item.get('title', '')}\n"
        combined += f"Link: {item.get('link', '')}\n"
        combined += f"Content: {item.get('text', '')[:600]}\n"

    prompt = f"""You are extracting academic opportunity listings from content scraped from: {source_name}

Content:
{combined}

Extract real academic opportunities from this content. Return a JSON array where each object has:
- type: one of "phd", "postdoc", "paper", "grant", "conf"
- title: clear concise title
- institution: university or organization name
- location: city and country, or "Global"
- region: one of "africa", "europe", "north america", "asia", "global"
- field: academic discipline
- deadline: in YYYY-MM-DD format or null
- funding: funding details or null
- description: 1-2 sentence summary under 200 characters
- link: direct URL

Rules:
- Only include real specific opportunities
- Do not invent any details
- If nothing qualifies return []
- Return ONLY valid JSON array, no markdown, no explanation"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        print(f"   Claude extracted: {len(result)} opportunities")
        return result
    except Exception as e:
        print(f"   Claude error: {e}")
        return []

def get_existing_titles():
    """Fetch existing listing titles to avoid duplicates."""
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/listings?select=title&order=created_at.desc&limit=200",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            },
            timeout=10
        )
        data = response.json()
        titles = set(item["title"].lower() for item in data)
        print(f"✅ Supabase connected. {len(titles)} existing listings.")
        return titles
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return set()

def post_to_supabase(listing):
    """Post a single listing to Supabase."""
    payload = {
        "type": listing.get("type", "phd"),
        "title": listing.get("title", "")[:200],
        "institution": listing.get("institution", "")[:200],
        "location": listing.get("location", "Global")[:100],
        "region": listing.get("region", "global"),
        "field": listing.get("field", "")[:100],
        "deadline": listing.get("deadline"),
        "funding": listing.get("funding", "")[:100] if listing.get("funding") else None,
        "description": listing.get("description", "")[:500],
        "link": listing.get("link", "")[:500],
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
            json=payload,
            timeout=10
        )
        if response.status_code in [200, 201]:
            print(f"   ✅ Posted: {listing['title'][:60]}")
            return True
        else:
            print(f"   ❌ Failed: {response.status_code} — {response.text[:100]}")
            return False
    except Exception as e:
        print(f"   Post error: {e}")
        return False

def run_agent():
    print(f"\n🤖 Alaye Agent starting at {datetime.now(timezone.utc).isoformat()}")

    existing_titles = get_existing_titles()
    all_opportunities = []

    sources_to_use = random.sample(FREE_SOURCES, min(4, len(FREE_SOURCES)))

    for source in sources_to_use:
        print(f"\n🔍 Fetching: {source['name']}")
        if source["type"] == "rss":
            items = fetch_rss(source["url"])
        else:
            items = fetch_html(source["url"])

        if not items:
            continue

        opportunities = extract_with_claude(items, source["name"])

        for opp in opportunities:
            title = opp.get("title", "").strip()
            if not title or not opp.get("institution"):
                continue
            if title.lower() in existing_titles:
                print(f"   ⏭️  Duplicate: {title[:50]}")
                continue
            all_opportunities.append(opp)
            existing_titles.add(title.lower())

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
    print(f"Anthropic key exists: {'✅' if ANTHROPIC_API_KEY else '❌'}")
    existing = get_existing_titles()
    print(f"Supabase connection: {'✅ OK' if isinstance(existing, set) else '❌ Failed'}")
    run_agent()
