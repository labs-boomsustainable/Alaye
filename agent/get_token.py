import os
import urllib.request
import urllib.parse
import json

CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
AUTH_CODE = os.environ["GMAIL_AUTH_CODE"]

data = urllib.parse.urlencode({
    "code": AUTH_CODE,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
    "grant_type": "authorization_code"
}).encode()

req = urllib.request.Request(
    "https://oauth2.googleapis.com/token",
    data=data,
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        print("REFRESH TOKEN:", result.get("refresh_token", "NOT FOUND"))
except Exception as e:
    print(f"Error: {e}")
