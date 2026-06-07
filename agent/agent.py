import os
import json
import time
import random
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import anthropic

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

RSS_SOURCES = [
    {"name": "OpportunityDesk", "url": "https://opportunitydesk.org/feed/", "region": "global"},
    {"name": "ScholarshipPositions", "url": "https://scholarship-positions.com/feed/", "region": "global"},
    {"name": "FindAPhD", "url": "https://www.findaphd.com/phds/rss.aspx?Keywords=funded&PG=1", "region": "global"},
    {"name": "CallForPapers Penn", "url": "https://call-for-papers.sas.upenn.edu/sites/call-for-papers.sas.upenn.edu/files/feed_0.xml", "region": "global"},
]

def fetch_rss(source):
    """Fetch and parse RSS feed with tolerant parser."""
    name = source["name"]
    url = source["url"]
    print(f"   Fetching RSS: {name}")
    results = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        content = r.content
        content = content.replace(b'&', b'&amp;')
        content = content.replace(b'&amp;amp;', b'&amp;')
        content = content.replace(b'&amp;lt;', b'&lt;')
        content = content.replace(b'&amp;gt;', b'&gt;')
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            soup = BeautifulSoup(r.text, "html.parser")
            items_raw = soup.find_all("item")
            for item in items_raw[:8]:
                title = item.find("title")
                link = item.find("link")
                desc = item.find("description")
                pub = item.find("pubdate")
                if title:
                    results.append({
                        "source": name,
                        "link": link.get_text(strip=True) if link else url,
                        "text": f"Title: {title.get_text(strip=True)}\nPublished: {pub.get_text(strip=True) if pub else ''}\nContent: {desc.get_text(strip=True)[:1000] if desc else ''}"
                    })
            print(f"   {name}: {len(results)} items (via HTML parser)")
            return results

        items = list(root.iter("item"))[:8]
        for item in items:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            description = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            content = ""
            for tag in item:
                if "encoded" in tag.tag.lower():
                    content = tag.text or ""
                    break
            soup = BeautifulSoup(description + " " + content, "html.parser")
            clean_text = soup.get_text(separator=" ", strip=True)[:1500]
            if title:
                results.append({
                    "source": name,
                    "link": link,
                    "text": f"Title: {title}\nPublished: {pub_date}\nContent: {clean_text}"
                })
        print(f"   {name}: {len(results)} items")
    except Exception as e:
        print(f"   {name} RSS error: {e}")
    return results

def fetch_wikicfp():
    """Fetch conference CFPs from WikiCFP — current year only."""
    print("   Fetching WikiCFP...")
    results = []
    current_year = datetime.now(timezone.utc).year
    try:
        url = f"http://www.wikicfp.com/cfp/call?conference=international&year={current_year}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.find_all("tr")[:20]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                title_el = cells[0].find("a")
                deadline_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                location_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                if title_el:
                    if str(current_year - 1) in deadline_text or str(current_year - 2) in deadline_text:
                        continue
                    if str(current_year - 1) in title_el.get_text() or str(current_year - 2) in title_el.get_text():
                        continue
                    link = "http://www.wikicfp.com" + title_el.get("href", "")
                    results.append({
                        "source": "WikiCFP",
                        "link": link,
                        "text": f"Conference CFP: {title_el.get_text(strip=True)}. Submission Deadline: {deadline_text}. Location: {location_text}. Year: {current_year}"
                    })
        print(f"   WikiCFP: {len(results)} items")
    except Exception as e:
        print(f"   WikiCFP error: {e}")
    return results

def fetch_jobsacuk():
    """Fetch from jobs.ac.uk RSS feed."""
    print("   Fetching jobs.ac.uk RSS...")
    results = []
    try:
        url = "https://www.jobs.ac.uk/search/?keywords=phd+funded&format=rss"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items_raw = soup.find_all("item")
        for item in items_raw[:8]:
            title = item.find("title")
            link = item.find("link")
            desc = item.find("description")
            pub = item.find("pubdate")
            if title:
                results.append({
                    "source": "jobs.ac.uk",
                    "link": link.get_text(strip=True) if link else url,
                    "text": f"Title: {title.get_text(strip=True)}\nPublished: {pub.get_text(strip=True) if pub else ''}\nContent: {desc.get_text(strip=True)[:1000] if desc else ''}"
                })
        print(f"   jobs.ac.uk: {len(results)} items")
    except Exception as e:
        print(f"   jobs.ac.uk error: {e}")
    return results

def extract_with_claude(items, source_name):
    """Use Claude to extract structured opportunity data."""
    if not items:
        return []

    combined = ""
    for i, item in enumerate(items[:10]):
        combined += f"\n--- Item {i+1} from {item.get('source', source_name)} ---\n"
        combined += f"Link: {item.get('link', '')}\n"
        combined += f"Content: {item.get('text', '')[:1000]}\n"

    prompt = f"""Extract academic opportunities from this content. Source: {source_name}

{combined}

Return a JSON array. Each object must have:
- type: "phd", "msc", "postdoc", "paper", "grant", or "conf"
- title: specific opportunity title
- institution: university or organization name
- location: city and country or "Global"
- region: "africa", "europe", "north america", "asia", or "global"
- field: academic discipline
- deadline: YYYY-MM-DD or null. Only include opportunities closing in 2026 or later. Reject anything from 2025 or earlier entirely.
- funding: funding info or null
- description: max 200 char summary
- link: URL

Only include real opportunities with a clear title and institution.
MSc and Masters scholarships should use type "msc".
Return ONLY a valid JSON array. No markdown. No explanation. If none found return []"""

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
    all_items = []

    rss_sources = random.sample(RSS_SOURCES, min(3, len(RSS_SOURCES)))
    for source in rss_sources:
        items = fetch_rss(source)
        all_items += items
        time.sleep(2)

    all_items += fetch_wikicfp()
    time.sleep(2)
    all_items += fetch_jobsacuk()

    print(f"\n📥 Total raw items: {len(all_items)}")

    all_opportunities = []
    opportunities = extract_with_claude(all_items, "Mixed sources")

    current_year = datetime.now(timezone.utc).year
    for opp in opportunities:
        title = opp.get("title", "").strip()
        if not title or not opp.get("institution"):
            continue
        if title.lower() in existing_titles:
            print(f"   ⏭️  Duplicate: {title[:50]}")
            continue
        deadline = opp.get("deadline")
        if deadline:
            try:
                if int(deadline[:4]) < current_year:
                    print(f"   ⏭️  Expired: {title[:50]}")
                    continue
            except:
                pass
        if str(current_year - 1) in title or str(current_year - 2) in title:
            print(f"   ⏭️  Old listing: {title[:50]}")
            continue
        all_opportunities.append(opp)
        existing_titles.add(title.lower())

    print(f"\n📦 Unique opportunities found: {len(all_opportunities)}")

    posted = 0
    for opp in all_opportunities[:10]:
        if post_to_supabase(opp):
            posted += 1
        time.sleep(1)

    print(f"\n✅ Agent complete. Posted {posted} new listings.")

if __name__ == "__main__":
    print("🧪 Testing connections...")
    print(f"Supabase URL: {SUPABASE_URL[:30]}...")
    print(f"Anthropic key exists: {'✅' if ANTHROPIC_API_KEY else '❌'}")
    get_existing_titles()
    run_agent()
