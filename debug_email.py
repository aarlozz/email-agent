from gmail_tools import service

MESSAGE_ID = "1a1c2825508c4c97"   # the id you printed

msg = service.users().messages().get(
    userId="me", id=MESSAGE_ID, format="full"
).execute()

def show(part, depth=0):
    body = part.get("body", {})
    print(
        "  " * depth
        + f"{part.get('mimeType')} | size={body.get('size')} "
        + f"| has_data={'data' in body} | attachmentId={'attachmentId' in body}"
    )
    for p in part.get("parts", []):
        show(p, depth + 1)

show(msg["payload"])