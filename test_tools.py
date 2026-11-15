from gmail_tools import search_emails, read_email

emails = search_emails("older_than:4d", max_results=5)
for i, e in enumerate(emails):
    print(i, "|", e["id"], "|", e["from"], "|", e["subject"])

if len(emails) > 1:
    print("\n--- SECOND EMAIL ---")
    print(read_email(emails[1]["id"]))
else:
    print("Fewer than 2 emails found.")