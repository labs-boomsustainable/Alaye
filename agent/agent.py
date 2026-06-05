import os
import json
import time
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import anthropic

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AcademicBot/1.0; +https://alaye-navy.vercel.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def fetch_daad():
    """Fetch scholarships from DAAD — German Academic Exchange."""
    print("   Fetching DAAD...")
    results = []
    try:
        url = "https://www.daad.de/en/studying-in-germany/scholarships/daad-scholarships/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","nav","footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)[:4000]
        results.append({"source": "DAAD Germany", "link": url, "text": text})
        print(f"   DAAD: {len(text)} chars")
    except Exception as e:
        print(f"   DAAD error: {e}")
    return results

def fetch_findaphd():
    """Fetch from FindAPhD search results."""
    print("   Fetching FindAPhD...")
    results = []
    urls = [
        "https://www.findaphd.com/phds/non-eu-students/?00w4W0",
        "https://www.findaphd.com/phds/africa/?00w400",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.find_all("div", class_="phd-result")[:5]
            for card in cards:
                title_el = card.find("h3") or card.find("h4")
                link_el = card.find("a", href=True)
                desc_el = card.find("p")
                if title_el:
                    link = link_el["href"] if link_el else url
                    if link.startswith("/"):
                        link = "https://www.findaphd.com" + link
                    results.append({
                        "source": "FindAPhD",
                        "link": link,
                        "text": f"{title_el.get_text(strip=True)}. {desc_el.get_text(strip=True) if desc_el else ''}"
                    })
            if not cards:
                for tag in soup(["script","style","nav","footer"]):
                    tag.decompose()
                text = soup.get_text(separator=" ", strip=True)[:3000]
                if len(text) > 200:
                    results.append({"source": "FindAPhD", "link": url, "text": text})
            print(f"   FindAPhD {url[-20:]}: {len(results)} items")
        except Exception as e:
            print(f"   FindAPhD error: {e}")
        time.sleep(2)
    return results

def fetch_scholarshippositions():
    """Fetch from scholarship-positions.com — very open site."""
    print("   Fetching ScholarshipPositions...")
    results = []
    urls = [
        "https://scholarship-positions.com/category/phd-scholarships/",
        "https://scholarship-positions.com/category/postdoctoral-fellowships/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            articles = soup.find_all("article")[:6]
            for article in articles:
                title_el = article.find("h2") or article.find("h3")
                link_el = article.find("a", href=True)
                excerpt_el = article.find("div", class_="entry-summary") or article.find("p")
                if title_el:
                    link = link_el["href"] if link_el else url
                    results.append({
                        "source": "ScholarshipPositions",
                        "link": link,
                        "text": f"{title_el.get_text(strip=True)}. {excerpt_el.get_text(strip=True)[:300] if excerpt_el else ''}"
                    })
            print(f"   ScholarshipPositions: {len(results)} items so far")
        except Exception as e:
            print(f"   ScholarshipPositions error: {e}")
        time.sleep(2)
    return results

def fetch_academictransfer():
    """Fetch from Academic Transfer — open European jobs board."""
    print("   Fetching AcademicTransfer...")
    results = []
    try:
        url = "https://www.academictransfer.com/en/jobs/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        jobs = soup.find_all("li", class_="job")[:8]
        for job in jobs:
            title_el = job.find("h3") or job.find("h2")
            link_el = job.find("a", href=True)
            meta = job.find("div", class_="meta") or job.find("p")
            if title_el:
                link = link_el["href"] if link_el else url
                if link.startswith("/"):
                    link = "https://www.academictransfer.com" + link
                results.append({
                    "source": "AcademicTransfer",
                    "link": link,
                    "text": f"{title_el.get_text(strip=True)}. {meta.get_text(strip=True)[:200] if meta else ''}"
                })
        if not jobs:
            for tag in soup(["script","style","nav","footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)[:3000]
            if len(text) > 200:
                results.append({"source": "AcademicTransfer", "link": url, "text": text})
        print(f"   AcademicTransfer: {len(results)} items")
    except Exception as e:
        print(f"   AcademicTransfer error: {e}")
    return results

def fetch_wikicfp():
    """Fetch conference CFPs from WikiCFP — fully public."""
    print("   Fetching WikiCFP...")
    results = []
    try:
        url = "http://www.wikicfp.com/cfp/call?conference=international"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.find_all("tr")[:20]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                title_el = cells[0].find("a")
                if title_el:
                    link = "http://www.wikicfp.com" + title_el.get("href","")
                    results.append({
                        "source": "WikiCFP",
                        "link": link,
                        "text": f"Conference CFP: {title_el.get_text(strip=True)}. Deadline: {cells[2].get_text(strip=True) if len(cells)>2 else 'TBD'}. Location: {cells[1].get_text(strip=True) if len(cells)>1 else 'TBD'}"
                    })
        print(f"   WikiCFP: {len(results)} items")
    except Exception as e:
        print(f"   WikiCFP error: {e}")
    return results

def extract_with_claude(items, source_name):
    """Use Claude to extract structured opportunity data."""
    if not items:
        return []

    combined = ""
    for i, item in enumerate(items[:8]):
        combined += f"\n--- Item {i+1} from {item.get('source', source_name)} ---\n"
        combined += f"Link: {item.get('link','')}\n"
        combined += f"Content: {item.get('text','')[:600]}\n"

    prompt = f"""Extract academic opportunities from this content. Source: {source_name}

{combined}

Return a JSON array. Each object must have:
- type: "phd", "postdoc", "paper", "grant", or "conf"
- title: specific opportunity title
- institution: university or organization
- location: city and country or "Global"
- region: "africa", "europe", "north america", "asia", or "global"
- field: academic discipline
- deadline: YYYY-MM-DD format. Look hard for any date mention — submission date, abstract deadline, conference date, application closes. Use that. Only null if truly no date exists anywhere.
- funding: funding info or null
- description: max 200 char summary
- link: URL

Only include real opportunities with a clear title and institution.
Return ONLY a valid JSON array. No markdown. No explanation. If none found return []"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        raw = raw.replace("```json","").replace("```","").strip()
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
        "type": listing.get("type","phd"),
        "title": listing.get("title","")[:200],
        "institution": listing.get("institution","")[:200],
        "location": listing.get("location","Global")[:100],
        "region": listing.get("region","global"),
        "field": listing.get("field","")[:100],
        "deadline": listing.get("deadline"),
        "funding": listing.get("funding","")[:100] if listing.get("funding") else None,
        "description": listing.get("description","")[:500],
        "link": listing.get("link","")[:500],
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
        if response.status_code in [200,201]:
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

    all_items = []
    all_items += fetch_scholarshippositions()
    time.sleep(2)
    all_items += fetch_wikicfp()
    time.sleep(2)
    all_items += fetch_academictransfer()
    time.sleep(2)
    all_items += fetch_findaphd()
    time.sleep(2)
    all_items += fetch_daad()

    print(f"\n📥 Total raw items collected: {len(all_items)}")

    opportunities = extract_with_claude(all_items, "Mixed sources")

    current_year = datetime.now(timezone.utc).year
    for opp in opportunities:
        title = opp.get("title","").strip()
        if not title or not opp.get("institution"):
            continue
        if title.lower() in existing_titles:
            print(f"   ⏭️  Duplicate: {title[:50]}")
            continue
        deadline = opp.get("deadline")
        if deadline:
            try:
                dl_year = int(deadline[:4])
                if dl_year < current_year:
                    print(f"   ⏭️  Expired: {title[:50]}")
                    continue
            except:
                pass
        if str(current_year - 1) in title or str(current_year - 2) in title:
            print(f"   ⏭️  Old listing skipped: {title[:50]}")
            continue
        all_opportunities.append(opp)
        existing_titles.add(title.lower())

    print(f"\n📦 Unique opportunities found: {len(all_opportunities)}")

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
