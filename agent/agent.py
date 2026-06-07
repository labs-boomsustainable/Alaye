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
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def fetch_html(url, name):
    """Fetch HTML page and extract text."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        print(f"   {name}: {len(text)} chars")
        return [{"source": name, "link": url, "text": text[:4000]}]
    except Exception as e:
        print(f"   {name} error: {e}")
        return []

def fetch_callforpaper():
    """Fetch from callforpaper.org."""
    print("   Fetching CallForPaper.org...")
    results = []
    try:
        r = requests.get("https://callforpaper.org/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all(["article", "div"], class_=lambda c: c and any(x in c for x in ["card", "event", "cfp", "conference"]))[:8]
        for card in cards:
            title_el = card.find(["h2", "h3", "h4"])
            link_el = card.find("a", href=True)
            if title_el:
                link = link_el["href"] if link_el else "https://callforpaper.org"
                if link.startswith("/"):
                    link = "https://callforpaper.org" + link
                results.append({"source": "CallForPaper.org", "link": link, "text": card.get_text(separator=" ", strip=True)[:600]})
        if not results:
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)[:4000]
            results.append({"source": "CallForPaper.org", "link": "https://callforpaper.org", "text": text})
        print(f"   CallForPaper.org: {len(results)} items")
    except Exception as e:
        print(f"   CallForPaper.org error: {e}")
    return results

def fetch_opportunitydesk():
    """Fetch from opportunitydesk.org — Africa focused."""
    print("   Fetching OpportunityDesk...")
    results = []
    urls = [
        "https://opportunitydesk.org/category/fellowships-and-scholarships/phd-post-doctoral/",
        "https://opportunitydesk.org/category/fellowships-and-scholarships/masters-postgraduate/",
        "https://opportunitydesk.org/category/calls-and-competitions/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            articles = soup.find_all("article")[:5]
            for article in articles:
                title_el = article.find(["h2", "h3"])
                link_el = article.find("a", href=True)
                excerpt = article.find(["p", "div"], class_=lambda c: c and "excerpt" in str(c))
                if title_el:
                    link = link_el["href"] if link_el else url
                    results.append({
                        "source": "OpportunityDesk",
                        "link": link,
                        "text": f"{title_el.get_text(strip=True)}. {excerpt.get_text(strip=True)[:300] if excerpt else ''}"
                    })
            print(f"   OpportunityDesk {url[-30:]}: {len(results)} items so far")
        except Exception as e:
            print(f"   OpportunityDesk error: {e}")
        time.sleep(2)
    return results

def fetch_jobsacuk():
    """Fetch from jobs.ac.uk — UK academic jobs."""
    print("   Fetching jobs.ac.uk...")
    results = []
    urls = [
        "https://www.jobs.ac.uk/search/?keywords=phd+funded",
        "https://www.jobs.ac.uk/search/?keywords=postdoc",
        "https://www.jobs.ac.uk/search/?keywords=research+fellowship",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = soup.find_all(["li", "div"], class_=lambda c: c and any(x in str(c) for x in ["j-search-result", "result", "job"]))[:6]
            for job in jobs:
                title_el = job.find(["h2", "h3", "h4", "a"])
                if title_el:
                    link_el = job.find("a", href=True)
                    link = link_el["href"] if link_el else url
                    if link.startswith("/"):
                        link = "https://www.jobs.ac.uk" + link
                    results.append({
                        "source": "jobs.ac.uk",
                        "link": link,
                        "text": job.get_text(separator=" ", strip=True)[:600]
                    })
            if not jobs:
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                text = soup.get_text(separator=" ", strip=True)[:3000]
                if len(text) > 200:
                    results.append({"source": "jobs.ac.uk", "link": url, "text": text})
            print(f"   jobs.ac.uk: {len(results)} items so far")
        except Exception as e:
            print(f"   jobs.ac.uk error: {e}")
        time.sleep(2)
    return results

def fetch_academicpositions():
    """Fetch from academicpositions.com."""
    print("   Fetching AcademicPositions...")
    results = []
    try:
        r = requests.get("https://academicpositions.com/find-jobs", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        jobs = soup.find_all(["article", "li", "div"], class_=lambda c: c and any(x in str(c) for x in ["job", "position", "listing"]))[:8]
        for job in jobs:
            title_el = job.find(["h2", "h3", "h4"])
            link_el = job.find("a", href=True)
            if title_el:
                link = link_el["href"] if link_el else "https://academicpositions.com"
                if link.startswith("/"):
                    link = "https://academicpositions.com" + link
                results.append({
                    "source": "AcademicPositions",
                    "link": link,
                    "text": job.get_text(separator=" ", strip=True)[:600]
                })
        if not jobs:
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)[:3000]
            if len(text) > 200:
                results.append({"source": "AcademicPositions", "link": "https://academicpositions.com/find-jobs", "text": text})
        print(f"   AcademicPositions: {len(results)} items")
    except Exception as e:
        print(f"   AcademicPositions error: {e}")
    return results

def fetch_scholarshippositions():
    """Fetch from scholarship-positions.com."""
    print("   Fetching ScholarshipPositions...")
    results = []
    urls = [
        "https://scholarship-positions.com/category/phd-scholarships-positions/",
        "https://scholarship-positions.com/category/masters-scholarships/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            articles = soup.find_all("article")[:6]
            for article in articles:
                title_el = article.find(["h2", "h3"])
                link_el = article.find("a", href=True)
                excerpt = article.find("p")
                if title_el:
                    link = link_el["href"] if link_el else url
                    results.append({
                        "source": "ScholarshipPositions",
                        "link": link,
                        "text": f"{title_el.get_text(strip=True)}. {excerpt.get_text(strip=True)[:300] if excerpt else ''}"
                    })
            print(f"   ScholarshipPositions: {len(results)} items so far")
        except Exception as e:
            print(f"   ScholarshipPositions error: {e}")
        time.sleep(2)
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
                        "text": f"Conference CFP: {title_el.get_text(strip=True)}. Deadline: {deadline_text}. Location: {location_text}"
                    })
        print(f"   WikiCFP: {len(results)} items")
    except Exception as e:
        print(f"   WikiCFP error: {e}")
    return results

def fetch_euraxess():
    """Fetch from EURAXESS — EU research jobs."""
    print("   Fetching EURAXESS...")
    results = []
    try:
        r = requests.get("https://euraxess.ec.europa.eu/jobs", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        jobs = soup.find_all(["article", "div", "li"], class_=lambda c: c and any(x in str(c) for x in ["job", "result", "listing", "view-row"]))[:8]
        for job in jobs:
            title_el = job.find(["h3", "h2", "h4"])
            link_el = job.find("a", href=True)
            if title_el:
                link = link_el["href"] if link_el else "https://euraxess.ec.europa.eu/jobs"
                if link.startswith("/"):
                    link = "https://euraxess.ec.europa.eu" + link
                results.append({
                    "source": "EURAXESS",
                    "link": link,
                    "text": job.get_text(separator=" ", strip=True)[:600]
                })
        if not jobs:
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)[:3000]
            if len(text) > 200:
                results.append({"source": "EURAXESS", "link": "https://euraxess.ec.europa.eu/jobs", "text": text})
        print(f"   EURAXESS: {len(results)} items")
    except Exception as e:
        print(f"   EURAXESS error: {e}")
    return results

def extract_with_claude(items, source_name):
    """Use Claude to extract structured opportunity data."""
    if not items:
        return []

    combined = ""
    for i, item in enumerate(items[:8]):
        combined += f"\n--- Item {i+1} from {item.get('source', source_name)} ---\n"
        combined += f"Link: {item.get('link', '')}\n"
        combined += f"Content: {item.get('text', '')[:600]}\n"

    prompt = f"""Extract academic opportunities from this content. Source: {source_name}

{combined}

Return a JSON array. Each object must have:
- type: "phd", "msc", "postdoc", "paper", "grant", or "conf"
- title: specific opportunity title
- institution: university or organization
- location: city and country or "Global"
- region: "africa", "europe", "north america", "asia", or "global"
- field: academic discipline
- deadline: YYYY-MM-DD or null. Only include opportunities with deadlines or events in 2026 or later. If the opportunity is from 2025 or earlier, do not include it at all. Return empty array for old content.
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

    fetchers = [
        fetch_callforpaper,
        fetch_opportunitydesk,
        fetch_jobsacuk,
        fetch_academicpositions,
        fetch_scholarshippositions,
        fetch_wikicfp,
        fetch_euraxess,
    ]

    selected = random.sample(fetchers, min(4, len(fetchers)))
    for fetcher in selected:
        items = fetcher()
        all_items += items
        time.sleep(3)

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
