import os
import json
import base64
import requests
import anthropic
from datetime import datetime, timezone

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
GMAIL_CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
GMAIL_REFRESH_TOKEN = os.environ["GMAIL_REFRESH_TOKEN"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

GOOGLE_GROUPS = [
    "women-in-machine-learning@googlegroups.com",
]

def get_access_token():
    """Get a fresh Gmail access token using the refresh token."""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "refresh_token": GMAIL_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }
    )
    data = response.json()
    token = data.get("access_token")
    if token:
        print("✅ Gmail access token obtained")
    else:
        print(f"❌ Failed to get access token: {data}")
    return token

def search_emails(access_token, query, max_results=10):
    """Search Gmail for emails matching query."""
    response = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"q": query, "maxResults": max_results}
    )
    data = response.json()
    messages = data.get("messages", [])
    print(f"   Found {len(messages)} emails for query: {query}")
    return messages

def get_email_content(access_token, message_id):
    """Get full email content by message ID."""
    response = requests.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"format": "full"}
    )
    data = response.json()

    subject = ""
    sender = ""
    body = ""

    headers = data.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"] == "Subject":
            subject = h["value"]
        if h["name"] == "From":
            sender = h["value"]

    def extract_body(payload):
        if payload.get("body", {}).get("data"):
            try:
                return base64.urlsafe_b64decode(
                    payload["body"]["data"] + "=="
                ).decode("utf-8", errors="ignore")
            except:
                return ""
        for part in payload.get("parts", []):
            text = extract_body(part)
            if text:
                return text
        return ""

    body = extract_body(data.get("payload", {}))
    return {"subject": subject, "sender": sender, "body": body[:3000]}

def extract_opportunities_with_claude(emails, source):
    """Use Claude to extract opportunities from email content."""
    if not emails:
        return []

    combined = ""
    for i, email in enumerate(emails[:5]):
        combined += f"\n--- Email {i+1} ---\n"
        combined += f"Subject: {email['subject']}\n"
        combined += f"From: {email['sender']}\n"
        combined += f"Body: {email['body'][:800]}\n"

    prompt = f"""You are extracting academic opportunities from emails sent to a Google Group: {source}

Emails:
{combined}

Extract real academic opportunities — PhD positions, postdocs, grants, paper calls, conferences.
Return a JSON array where each object has:
- type: "phd", "postdoc", "paper", "grant", or "conf"
- title: specific opportunity title
- institution: university or organization
- location: city and country or "Global"
- region: "africa", "europe", "north america", "asia", or "global"
- field: academic discipline
- deadline: YYYY-MM-DD or null. Only include opportunities with deadlines in 2026 or later. If the opportunity is clearly from a past year, do not include it.
- funding: funding details or null
- description: max 200 character summary
- link: application URL or null

Rules:
- Only extract real opportunities with a clear title and institution
- Do not invent any details
- If no opportunities found return []
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
            }
        )
        data = response.json()
        titles = set(item["title"].lower() for item in data)
        print(f"✅ Supabase connected. {len(titles)} existing listings.")
        return titles
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return set()

def post_to_supabase(listing):
    """Post a listing to Supabase."""
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
        "link": listing.get("link", "")[:500] if listing.get("link") else None,
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
            print(f"   ✅ Posted: {listing['title'][:60]}")
            return True
        else:
            print(f"   ❌ Failed: {response.status_code} — {response.text[:100]}")
            return False
    except Exception as e:
        print(f"   Post error: {e}")
        return False

def run_gmail_scraper():
    print(f"\n📧 Gmail scraper starting at {datetime.now(timezone.utc).isoformat()}")

    access_token = get_access_token()
    if not access_token:
        print("❌ Cannot proceed without access token")
        return

    existing_titles = get_existing_titles()
    all_opportunities = []

    for group in GOOGLE_GROUPS:
        print(f"\n🔍 Scanning emails from: {group}")
        query = f"from:{group} newer_than:7d"
        messages = search_emails(access_token, query, max_results=10)

        if not messages:
            print(f"   No recent emails from {group}")
            continue

        emails = []
        for msg in messages[:5]:
            content = get_email_content(access_token, msg["id"])
            if content["body"] or content["subject"]:
                emails.append(content)

        print(f"   Fetched {len(emails)} email contents")
        opportunities = extract_opportunities_with_claude(emails, group)

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
            if str(current_year - 1) in title or str(current_year - 2) in title or str(current_year - 3) in title:
                print(f"   ⏭️  Old listing skipped: {title[:50]}")
                continue
            all_opportunities.append(opp)
            existing_titles.add(title.lower())

    print(f"\n📦 Total unique opportunities found: {len(all_opportunities)}")

    posted = 0
    for opp in all_opportunities[:10]:
        if post_to_supabase(opp):
            posted += 1

    print(f"\n✅ Gmail scraper complete. Posted {posted} new listings.")

if __name__ == "__main__":
    run_gmail_scraper()
