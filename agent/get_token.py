import urllib.request
import urllib.parse
import json

CLIENT_ID = "285885127099-g6ae5gpvmgqjuqhebtmmrsadkrd8e9da.apps.googleusercontent.com"
CLIENT_SECRET = "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"
AUTH_CODE = "4/1AdkVLPzZpfbmOqbpi5UslWBswoGyp0g2ZH8DGhFRrxlIuH3qUcyH11DSMpI"

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

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read())
    print("REFRESH TOKEN:", result.get("refresh_token", "NOT FOUND"))
    print("Full response:", json.dumps(result, indent=2))
