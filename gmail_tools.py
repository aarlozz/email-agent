# gmail_tools.py
# ---------------------------------------------------------------------------
# The agent's "hands". These are plain Python functions that talk to Gmail.
# The AI model never calls Gmail directly: it asks agent.py to run one of
# these functions, and agent.py sends the result back to the model.
# ---------------------------------------------------------------------------

import re                          # regular expressions, used to clean text
import base64                      # Gmail encodes email bodies in base64
from bs4 import BeautifulSoup      # turns HTML into plain text
from auth import get_gmail_service # our login helper from auth.py

# Log in once when this file is imported. `service` is the handle we use for
# every Gmail API call below. Because the scope in auth.py is readonly,
# nothing in this file can send, delete or change email.
service = get_gmail_service()


# ---------------------------------------------------------------------------
# Helpers (the leading underscore means "internal, not for the agent to call")
# ---------------------------------------------------------------------------

def _decode(data: str) -> str:
    """Turn Gmail's base64 text into a normal string.

    Gmail uses the "URL-safe" base64 variant (- and _ instead of + and /),
    which is why we use urlsafe_b64decode. errors="replace" swaps any
    undecodable byte for a placeholder instead of crashing the program.
    """
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def _find_part(payload, mime_type):
    """Search an email's structure for a part of a given type and return its text.

    An email is a TREE of parts. A typical newsletter looks like:

        multipart/alternative
        ├── text/plain   (simple text version)
        └── text/html    (fancy HTML version)

    Each part may contain more parts, so we search recursively: check this
    part, and if it isn't a match, check each of its children.
    Returns "" if no matching part has any data.
    """
    # Is THIS part the one we want, and does it carry actual data?
    # .get("body", {}) avoids a crash if the "body" key is missing.
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return _decode(payload["body"]["data"])

    # Otherwise look inside each child part (recursion)
    for part in payload.get("parts", []):
        found = _find_part(part, mime_type)
        if found:              # stop at the first match
            return found

    return ""                  # nothing found in this branch


def _clean(text: str) -> str:
    """Tidy extracted text so it wastes fewer tokens.

    Marketing emails pad the start with invisible characters (zero-width
    spaces and similar) and lots of blank lines. They are useless to the
    model but count against your token limits, so we remove them.
    """
    # Remove invisible characters (zero-width space, joiners, BOM, soft hyphen, etc.)
    text = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff\u00ad\u034f]", "", text)
    # Collapse runs of spaces/tabs into a single space
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse multiple blank lines into one line break
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def _extract_text(payload) -> str:
    """Get readable text from an email, preferring plain text over HTML."""
    # First choice: the plain-text version, if the sender included one
    plain = _find_part(payload, "text/plain")
    if plain.strip():
        return _clean(plain)

    # Second choice: the HTML version, converted to text
    html = _find_part(payload, "text/html")
    if html:
        soup = BeautifulSoup(html, "html.parser")
        # <script> and <style> contain code, not readable content, so drop them
        for tag in soup(["script", "style"]):
            tag.decompose()
        # separator="\n" puts each element on its own line; strip=True trims spaces
        text = soup.get_text(separator="\n", strip=True)
        return _clean(text)

    # The email has neither (for example it is only images or attachments)
    return ""


# ---------------------------------------------------------------------------
# Tools the agent can use
# ---------------------------------------------------------------------------

def search_emails(query: str, max_results: int = 5) -> list[dict]:
    """Search Gmail and return SHORT summaries (not full bodies).

    `query` uses Gmail's search syntax, the same as the Gmail search box:
    'is:unread', 'from:someone@x.com', 'newer_than:2d', 'subject:invoice'.

    Two API calls happen here:
      1. messages().list -> gives only message IDs
      2. messages().get(format="metadata") -> gives headers + snippet per ID
    Keeping results small is deliberate: it saves tokens and money.
    """
    # Cap the number of results, even if the model asks for 100,
    # so a mistake can't flood the model with data.
    max_results = min(max_results, 10)

    # Step 1: find matching message IDs. An empty query falls back to the inbox.
    resp = service.users().messages().list(
        userId="me",                  # "me" = the logged-in user
        q=query or "in:inbox",
        maxResults=max_results,
    ).execute()

    results = []
    # If nothing matches, Gmail omits the "messages" key entirely,
    # so .get("messages", []) gives an empty list instead of crashing.
    for m in resp.get("messages", []):
        # Step 2: fetch details for this one message
        msg = service.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata",        # headers only, not the whole email body
            metadataHeaders=["From", "Subject", "Date"],   # which headers we want
        ).execute()

        # Headers arrive as a list like [{"name": "From", "value": "..."}, ...]
        # This turns it into a dictionary: {"From": "...", "Subject": "..."}
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

        results.append({
            "id": m["id"],                          # the model uses this to read the email later
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),      # Gmail's short preview text
        })

    # Note: this return is OUTSIDE the for loop. If it were inside, the
    # function would stop after the first email.
    return results


def read_email(message_id: str, max_chars: int = 1500) -> dict:
    """Read ONE email's full text, cut off at max_chars.

    The cut-off protects your free-tier token limit: one giant newsletter
    shouldn't be able to use up the whole budget.
    """
    # get() fetches one specific message. format="full" includes the body parts.
    msg = service.users().messages().get(
        userId="me",
        id=message_id,       # the variable, NOT the string "message_id"
        format="full",
    ).execute()

    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    body = _extract_text(msg["payload"]).strip()

    # Some emails have no readable text (image-only promos, odd formats).
    # Instead of returning a silent empty body, which would make the agent
    # claim the email is blank, fall back to Gmail's snippet and say why.
    note = ""
    if not body:
        body = msg.get("snippet", "")
        note = "No readable text body found (likely image-based email). Showing snippet only."

    return {
        "id": message_id,
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body": body[:max_chars],    # [:max_chars] slices off anything past the limit
        "note": note,
    }