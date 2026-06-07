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
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Cache-Control": "no-cache",
}

def fetch_wikicfp():
    """Fetch conference CFPs from WikiCFP."""
    print("   Fetching WikiCFP...")
    results = []
    current_year = datetime.now(timezone.utc).year
    try:
        url = f"http://www.wikicfp.com/cfp/call?conference=international&year={current_year}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.find_all("tr")
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

def fetch_nature_jobs():
    """Fetch from Nature Careers — open listings."""
    print("   Fetching Nature Careers...")
    results = []
    try:
        url = "https://www.nature.com/naturecareers/jobs"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        jobs = soup.find_all(["li", "article", "div"], class_=lambda c: c and any(x in str(c).lower() for x in ["job", "result", "listing"]))[:8]
        for job in jobs:
            title_el = job.find(["h2", "h3", "h4", "a"])
            if title_el:
                link_el = job.find("a", href=True)
                link = link_el["href"] if link_el else url
                if link.startswith("/"):
                    link = "https://www.nature.com" + link
                results.append({
                    "source": "Nature Careers",
                    "link": link,
                    "text": job.get_text(separator=" ", strip=True)[:800]
                })
        if not jobs:
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)[:3000]
            if len(text) > 300:
                results.append({"source": "Nature Careers", "link": url, "text": text})
        print(f"   Nature Careers: {len(results)} items")
    except Exception as e:
        print(f"   Nature Careers error: {e}")
    return results

def fetch_inomics():
    """Fetch from INOMICS — economics and social science jobs."""
    print("   Fetching INOMICS...")
    results = []
    urls = [
        "https://inomics.com/opportunity/phd",
        "https://inomics.com/opportunity/grants",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            cards = soup.find_all(["article", "div", "li"], class_=lambda c: c and any(x in str(c).lower() for x in ["card", "item", "listing", "opportunity"]))[:6]
            for card in cards:
                title_el = card.find(["h2", "h3", "h4"])
                link_el = card.find("a", href=True)
                if title_el:
                    link = link_el["href"] if link_el else url
                    if link.startswith("/"):
                        link = "https://inomics.com" + link
                    results.append({
                        "source": "INOMICS",
                        "link": link,
                        "text": card.get_text(separator=" ", strip=True)[:800]
                    })
            if not cards:
                text = soup.get_text(separator=" ", strip=True)[:3000]
                if len(text) > 300:
                    results.append({"source": "INOMICS", "link": url, "text": text})
            print(f"   INOMICS {url[-20:]}: {len(results)} items so far")
        except Exception as e:
            print(f"   INOMICS error: {e}")
        time.sleep(2)
    return results

def fetch_impactsciencehub():
    """Fetch from ImpactScienceHub — African focused opportunities."""
    print("   Fetching ImpactScienceHub...")
    results = []
    try:
        url = "https://www.impactsciencehub.com/opportunities"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)[:4000]
        if len(text) > 300:
            results.append({"source": "ImpactScienceHub", "link": url, "text": text})
        print(f"   ImpactScienceHub: {len(results)} items")
    except Exception as e:
        print(f"   ImpactScienceHub error: {e}")
    return results

def fetch_aau_scholarships():
    """Fetch African scholarships from AAU."""
    print("   Fetching AAU Scholarships...")
    results = []
    try:
        url = "https://www.aau.org/scholarships-fellowships-awards/"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        items = soup.find_all(["article", "li", "div"], class_=lambda c: c and any(x in str(c).lower() for x in ["scholarship", "fellowship", "award", "post"]))[:8]
        for item in items:
            title_el = item.find(["h2", "h3", "h4"])
            link_el = item.find("a", href=True)
            if title_el:
                link = link_el["href"] if link_el else url
                results.append({
                    "source": "AAU",
                    "link": link,
                    "text": item.get_text(separator=" ", strip=True)[:800]
                })
        if not items:
            text = soup.get_text(separator=" ", strip=True)[:3000]
            if len(text) > 300:
                results.append({"source": "AAU", "link": url, "text": text})
        print(f"   AAU: {len(results)} items")
    except Exception as e:
        print(f"   AAU error: {e}")
    return results

def fetch_phd_portal():
    """Fetch from PhDPortal — global PhD listings."""
    print("   Fetching PhDPortal...")
    results = []
    try:
        url = "https://www.phdportal.eu/search/?q=&limit=20&order=publications_date&mode=desc"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        items = soup.find_all(["article", "li", "div"], class_=lambda c: c and any(x in str(c).lower() for x in ["programme", "result", "item", "phd"]))[:8]
        for item in items:
            title_el = item.find(["h2", "h3", "h4"])
            link_el = item.find("a", href=True)
            if title_el:
                link = link_el["href"] if link_el else url
                if link.startswith("/"):
                    link = "https://www.phdportal.eu" + link
                results.append({
                    "source": "PhDPortal",
                    "link": link,
                    "text": item.get_text(separator=" ", strip=True)[:800]
                })
        if not items:
            text = soup.get_text(separator=" ", strip=True)[:3000]
            if len(text) > 300:
                results.append({"source": "PhDPortal", "link": url, "text": text})
        print(f"   PhDPortal: {len(results)} items")
    except Exception as e:
        print(f"   PhDPortal error: {e}")
    return results

def extract_with_claude(items, source_name):
    """Use Claude to extract structured opportunity data."""
    if not items:
        return []

    combined = ""
    for i, item in enumerate(items[:12]):
        combined += f"\n--- Item {i+1} from {item.get('source', source_name)} ---\n"
        combined += f"Link: {item.get('link', '')}\n"
        combined += f"Content: {item.get('text', '')[:1000]}\n"

    current_year = datetime.now(timezone.utc).year

    prompt = f"""Extract academic opportunities from this content. Today is {datetime.now().strftime('%B %Y')}.

{combined}

Return a JSON array. Each object must have:
- type: "phd", "msc", "postdoc", "paper", "grant", or "conf"
- title: specific opportunity title
- institution: university or organization name
- location: city and country or "Global"
- region: "africa", "europe", "north america", "asia", or "global"
- field: academic discipline
- deadline: YYYY-MM-DD or null. Only include opportunities with deadlines or events in {current_year} or later.
- funding: funding info or null
- description: max 200 char summary
- link: direct URL

Important rules:
- Only include opportunities closing in {current_year} or later
- Reject anything from {current_year - 1} or earlier entirely
- MSc and Masters opportunities use type "msc"
- Must have a real title and real institution
- Return ONLY valid JSON array, no markdown, no explanation
- If nothing qualifies return []"""

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

    all_items += fetch_wikicfp()
    time.sleep(2)
    all_items += fetch_nature_jobs()
    time.sleep(2)
    all_items += fetch_inomics()
    time.sleep(2)
    all_items += fetch_phd_portal()
    time.sleep(2)
    all_items += fetch_aau_scholarships()
    time.sleep(2)
    all_items += fetch_impactsciencehub()

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
