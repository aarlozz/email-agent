import base64
from bs4 import BeautifulSoup
from gmail_tools import service

MESSAGE_ID = "1a1c2825508c4c97"

msg = service.users().messages().get(
    userId="me", id=MESSAGE_ID, format="full"
).execute()

# Find the html part by hand
html_part = None
for part in msg["payload"].get("parts", []):
    if part.get("mimeType") == "text/html":
        html_part = part

raw = html_part["body"]["data"]
html = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")
print("1. decoded HTML length:", len(html))
print("2. first 300 chars of HTML:\n", html[:300])

soup = BeautifulSoup(html, "html.parser")
for tag in soup(["script", "style"]):
    tag.decompose()
text = soup.get_text(separator="\n", strip=True)
print("\n3. extracted text length:", len(text))
print("4. first 500 chars of text:\n", text[:500])

from gmail_tools import _find_part, _extract_text

print("\n5. _find_part html length:", len(_find_part(msg["payload"], "text/html")))
print("6. _extract_text length:", len(_extract_text(msg["payload"])))