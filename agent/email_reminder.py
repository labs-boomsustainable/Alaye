import os
import json
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
RESEND_API_KEY = os.environ["RESEND_API_KEY"]

def days_left(deadline_str):
    if not deadline_str:
        return None
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (deadline - now).days
    except:
        return None

def get_all_users_with_bookmarks():
    """Get all users who have bookmarks."""
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/bookmarks?select=user_id",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            }
        )
        data = response.json()
        user_ids = list(set(item["user_id"] for item in data))
        print(f"Found {len(user_ids)} users with bookmarks")
        return user_ids
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

def get_user_email(user_id):
    """Get email for a user."""
    try:
        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            }
        )
        data = response.json()
        return data.get("email")
    except Exception as e:
        print(f"Error fetching user email: {e}")
        return None

def get_user_bookmarked_listings(user_id):
    """Get all bookmarked listings for a user."""
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/bookmarks?user_id=eq.{user_id}&select=listing_id",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            }
        )
        bookmark_data = response.json()
        listing_ids = [b["listing_id"] for b in bookmark_data]
        if not listing_ids:
            return []

        ids_filter = ",".join(listing_ids)
        response2 = requests.get(
            f"{SUPABASE_URL}/rest/v1/listings?id=in.({ids_filter})&select=*",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
            }
        )
        return response2.json()
    except Exception as e:
        print(f"Error fetching listings: {e}")
        return []

def build_email_html(listings, email_type="weekly"):
    """Build a friendly HTML email."""
    urgent = [l for l in listings if days_left(l.get("deadline")) is not None and 0 <= days_left(l.get("deadline")) <= 5]
    upcoming = [l for l in listings if days_left(l.get("deadline")) is not None and 5 < days_left(l.get("deadline")) <= 30]
    rest = [l for l in listings if l not in urgent and l not in upcoming]

    def card(l):
        d = days_left(l.get("deadline"))
        if d is not None and d >= 0:
            deadline_str = f"{d} days left — {l.get('deadline', '')}"
            deadline_color = "#dc2626" if d <= 5 else "#d97706" if d <= 14 else "#0f6e56"
        elif d is not None and d < 0:
            deadline_str = "Deadline passed"
            deadline_color = "#999"
        else:
            deadline_str = "No deadline specified"
            deadline_color = "#999"

        link = l.get("link", "")
        type_labels = {"phd": "PhD", "postdoc": "Postdoc", "paper": "Paper Call", "grant": "Grant", "conf": "Conference"}
        type_label = type_labels.get(l.get("type", ""), "Opportunity")

        return f"""
        <div style="background:#ffffff;border:1px solid #e8e0d4;border-radius:10px;padding:18px 20px;margin-bottom:12px;">
          <div style="margin-bottom:8px;">
            <span style="background:#f0e4b8;color:#7a5800;font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;">{type_label}</span>
          </div>
          <div style="font-family:Georgia,serif;font-size:16px;font-weight:600;color:#1a1612;margin-bottom:4px;">{l.get("title","")}</div>
          <div style="font-size:13px;color:#6b6358;margin-bottom:8px;">{l.get("institution","")} · {l.get("location","Global")}</div>
          {f'<div style="font-size:13px;color:#6b6358;margin-bottom:8px;">📚 {l.get("field","")}</div>' if l.get("field") else ""}
          {f'<div style="font-size:13px;color:#6b6358;margin-bottom:8px;">💰 {l.get("funding","")}</div>' if l.get("funding") else ""}
          <div style="font-size:13px;font-weight:600;color:{deadline_color};margin-bottom:12px;">⏰ {deadline_str}</div>
          {f'<div style="font-size:13px;color:#555;line-height:1.6;margin-bottom:12px;">{l.get("description","")}</div>' if l.get("description") else ""}
          {f'<a href="{link}" style="background:#0f6e56;color:#ffffff;text-decoration:none;padding:8px 18px;border-radius:8px;font-size:13px;font-weight:500;">View & Apply →</a>' if link else ""}
        </div>
        """

    urgent_section = ""
    if urgent:
        urgent_section = f"""
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px 18px;margin-bottom:20px;">
          <div style="font-size:14px;font-weight:600;color:#dc2626;margin-bottom:4px;">🚨 Urgent — deadline in 5 days or less</div>
          <div style="font-size:13px;color:#7f1d1d;">Act now on these opportunities before they close.</div>
        </div>
        {"".join(card(l) for l in urgent)}
        """

    upcoming_section = ""
    if upcoming:
        upcoming_section = f"""
        <div style="font-size:15px;font-weight:600;color:#1a1612;margin:20px 0 12px;font-family:Georgia,serif;">📅 Coming up in the next 30 days</div>
        {"".join(card(l) for l in upcoming)}
        """

    rest_section = ""
    if rest:
        rest_section = f"""
        <div style="font-size:15px;font-weight:600;color:#1a1612;margin:20px 0 12px;font-family:Georgia,serif;">📌 Your other saved opportunities</div>
        {"".join(card(l) for l in rest)}
        """

    greeting = "Here is your weekly digest" if email_type == "weekly" else "Here is a summary of your saved opportunities"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#f2ede6;font-family:'DM Sans',Arial,sans-serif;">
      <div style="max-width:600px;margin:0 auto;padding:32px 16px;">

        <div style="background:#1a1612;border-radius:12px 12px 0 0;padding:28px 28px 24px;margin-bottom:0;">
          <div style="font-family:Georgia,serif;font-size:26px;font-weight:700;color:#f7f3ec;">Alaye<span style="color:#b8860b;">.</span></div>
          <div style="font-size:11px;color:rgba(247,243,236,0.5);letter-spacing:0.8px;text-transform:uppercase;margin-top:3px;">Open Academic Opportunities</div>
        </div>

        <div style="background:#ffffff;padding:28px;border-radius:0 0 12px 12px;margin-bottom:20px;">
          <div style="font-family:Georgia,serif;font-size:20px;font-weight:600;color:#1a1612;margin-bottom:8px;">
            Your saved opportunities
          </div>
          <div style="font-size:14px;color:#6b6358;line-height:1.7;margin-bottom:24px;">
            {greeting} from Alaye. You have <strong>{len(listings)}</strong> saved opportunit{"ies" if len(listings) != 1 else "y"}. {"Don't let deadlines slip by!" if urgent else "Keep track of your applications and stay ahead."}
          </div>

          {urgent_section}
          {upcoming_section}
          {rest_section}

          <div style="margin-top:28px;padding-top:20px;border-top:1px solid #e8e0d4;text-align:center;">
            <a href="https://alaye-navy.vercel.app" style="background:#b8860b;color:#1a1612;text-decoration:none;padding:12px 28px;border-radius:10px;font-size:14px;font-weight:600;">Browse more opportunities →</a>
          </div>
        </div>

        <div style="text-align:center;font-size:11px;color:#aaa;padding:0 16px 24px;">
          You are receiving this because you saved opportunities on Alaye.<br>
          Visit <a href="https://alaye-navy.vercel.app" style="color:#0f6e56;">alaye-navy.vercel.app</a> to manage your saved items.
        </div>

      </div>
    </body>
    </html>
    """
    return html

def send_email(to_email, subject, html):
    """Send email via Resend."""
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": "Alaye <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": html
            }
        )
        if response.status_code == 200:
            print(f"✅ Email sent to {to_email}")
            return True
        else:
            print(f"❌ Email failed: {response.text}")
            return False
    except Exception as e:
        print(f"Email error: {e}")
        return False

def run_weekly_digest():
    """Send weekly digest to all users with bookmarks."""
    print(f"\n📧 Weekly digest starting at {datetime.now(timezone.utc).isoformat()}")
    user_ids = get_all_users_with_bookmarks()
    sent = 0
    for user_id in user_ids:
        email = get_user_email(user_id)
        if not email:
            continue
        listings = get_user_bookmarked_listings(user_id)
        if not listings:
            continue
        html = build_email_html(listings, "weekly")
        subject = f"Alaye — Your weekly opportunities digest ({len(listings)} saved)"
        if send_email(email, subject, html):
            sent += 1
    print(f"✅ Weekly digest complete. Sent to {sent} users.")

def run_urgent_alerts():
    """Send urgent alerts for deadlines within 5 days."""
    print(f"\n🚨 Urgent alerts check at {datetime.now(timezone.utc).isoformat()}")
    user_ids = get_all_users_with_bookmarks()
    sent = 0
    for user_id in user_ids:
        email = get_user_email(user_id)
        if not email:
            continue
        listings = get_user_bookmarked_listings(user_id)
        urgent = [l for l in listings if days_left(l.get("deadline")) is not None and 0 <= days_left(l.get("deadline")) <= 5]
        if not urgent:
            continue
        html = build_email_html(urgent, "urgent")
        subject = f"🚨 Alaye — {len(urgent)} deadline{'s' if len(urgent) > 1 else ''} closing in 5 days!"
        if send_email(email, subject, html):
            sent += 1
    print(f"✅ Urgent alerts complete. Sent to {sent} users.")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    if mode == "urgent":
        run_urgent_alerts()
    else:
        run_weekly_digest()
