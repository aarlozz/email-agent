# Email Agent

A read-only AI agent that lets you chat with your Gmail inbox. Ask things like
"what's my most recent email?" or "summarize the one from Atlassian", and the
agent searches and reads your mail to answer.

It uses:

- **Gmail API** to search and read email (read-only permission)
- **Groq API** (free tier) to run the language model that decides what to do
- **Flask + HTML/JS** for an optional local web chat UI

## What it can and can't do

| Can | Cannot |
|---|---|
| Search your mail with Gmail syntax (`from:`, `is:unread`, `newer_than:`) | Send email |
| Read and summarize individual emails | Delete or modify email |
| Answer follow-up questions in the same chat | Remember anything after you restart it |

The "cannot" column is enforced by the Gmail permission itself (`gmail.readonly`),
not just by the prompt. Even a buggy or tricked model cannot send or delete mail.

## How it works

```
You  ->  agent.py  ->  Groq model  ->  asks to use a tool
                           ^                    |
                           |                    v
                           +---- result ---- gmail_tools.py ---- Gmail API
```

1. You ask a question.
2. `agent.py` sends your question, the rules, and a menu of tools to the model.
3. The model either answers, or asks to run a tool (`search_emails`, `read_email`).
4. `agent.py` runs the tool, sends the result back, and repeats until the model answers.
5. A step limit and size caps stop it from looping or using too many tokens.

## Project structure

```
email-agent/
├── credentials.json     (YOU download this from Google. See below)
├── token.json           (created automatically on first login)
├── .env                 (your Groq API key)
├── .gitignore
├── requirements.txt
├── auth.py              Gmail login (OAuth)
├── gmail_tools.py       search_emails and read_email functions
├── agent.py             the agent loop (terminal chat)
├── app.py               Flask server for the web UI
├── static/
│   └── index.html       the web chat page
├── test_tools.py        tests Gmail tools without any AI
└── test_key.py          tests your Groq key
```

## Setup

### 1. Install

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt`:

```
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
groq
python-dotenv
beautifulsoup4
flask
```

### 2. Get a Groq API key

1. Create a free account at https://console.groq.com
2. Open the API keys page and create a key (it starts with `gsk_`).
3. Create a file named `.env` in the project folder:

```
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

No quotes, no spaces around `=`. Groq's model list changes often. If you get a
"model not found" error, list the models your key can use and pick a chat model
that supports tool calling (for example `openai/gpt-oss-20b`), then update
`GROQ_MODEL`.

### 3. Get `credentials.json` from Google

`credentials.json` identifies your app to Google. You create it once, for free.
No billing or credit card is needed. Google renames console menus sometimes, so
look for the closest match if a label differs.

**a) Create a project**

1. Go to https://console.cloud.google.com and sign in with the Gmail account
   whose email you want the agent to read.
2. Click the project dropdown (top left), choose **New Project**, name it
   `email-agent`, and click **Create**.
3. Make sure the new project is selected.

**b) Enable the Gmail API**

1. Open **APIs & Services > Library**.
2. Search for **Gmail API**, open it, and click **Enable**.

**c) Configure the consent screen**

1. Open **APIs & Services > OAuth consent screen** (may be called
   **Google Auth Platform**).
2. App name: `email-agent`. Support email and contact email: your Gmail.
3. Audience / user type: **External**.
4. Under **Test users**, click **Add users** and add **your own Gmail address**.
   Do not skip this. Without it, login fails with "Access blocked" or
   "Error 403: access_denied".

You do not need to submit the app for Google verification. That is only for
apps used by the public.

**d) Create the credentials**

1. Open **APIs & Services > Credentials** (or **Clients**).
2. Click **Create Credentials > OAuth client ID**.
3. Application type: **Desktop app** (important: not "Web application").
4. Click **Create**, then **Download JSON**.

**e) Put the file in your project**

1. Rename the downloaded file (it has a long name like
   `client_secret_1234.apps.googleusercontent.com.json`) to exactly
   `credentials.json`.
2. Move it into the project folder next to `auth.py`.
3. On Windows, make sure it is not saved as `credentials.json.json`. Turn on
   **View > File name extensions** in File Explorer to check.

### 4. Get `token.json` (automatic)

You do not download this one. It is created the first time you log in:

```bash
python test_tools.py
```

1. A browser tab opens. Choose the Google account you added as a test user.
2. Google shows "Google hasn't verified this app". That is expected because
   you made the app. Click **Advanced > Go to email-agent (unsafe)**.
3. Approve read-only access to your email.
4. `token.json` appears in your folder, and your terminal prints your recent
   emails.

After that you will not be asked to log in again until the token expires.

| File | What it is | Who creates it |
|---|---|---|
| `credentials.json` | Identifies your app to Google | You, in Google Cloud Console |
| `token.json` | Proof that you approved access to your mailbox | The program, on first login |

**Both files are private.** Anyone who has `token.json` can read your email.
They are already listed in `.gitignore`. Never upload them to GitHub or share
them. If they leak, revoke access at https://myaccount.google.com/permissions
and create new ones.

## Running it

Test each layer before moving to the next.

**1. Gmail tools (no AI):**

```bash
python test_tools.py
```

**2. Groq key:**

```bash
python test_key.py
```

**3. The agent in the terminal:**

```bash
python agent.py
```

Try:

- `What's my most recent email?`
- `Summarize the second one.`
- `Find emails from Strava.`
- `Delete all my Booking.com emails.` (it should refuse)

You will see `[tool]` lines showing each tool the agent calls.

**4. The web UI:**

```bash
python app.py
```

Open http://127.0.0.1:5000. The server only listens on your own machine
because it can read your mailbox. Never expose it to the internet without a
proper login.

## Troubleshooting

| Problem | Fix |
|---|---|
| `FileNotFoundError: credentials.json` | Wrong folder, wrong name, or `credentials.json.json` |
| "Access blocked" / `Error 403: access_denied` | Add your Gmail under **Test users** on the consent screen |
| `redirect_uri_mismatch` | You made a Web application client. Create a **Desktop app** one |
| "Gmail API has not been used in project" | Enable the Gmail API, wait a minute, retry |
| Login stops working after about a week | Delete `token.json` and log in again (Testing-mode tokens expire in about 7 days) |
| Changed `SCOPES` in `auth.py` | Delete `token.json` so Google asks for the new permissions |
| `model not found` (Groq) | The model was retired. Pick another from your key's model list and update `GROQ_MODEL` |
| Rate limit message | Groq's free tier is strict. Wait a minute, or switch to a smaller model |
| Empty email body | Some emails are image-only. The tool falls back to Gmail's snippet and adds a note |
| `TypeError: unexpected keyword argument` | Check capitalization: `userId`, `metadataHeaders`, `maxResults`, `port` |
| `Error: 400 ... description must be a string` | A stray comma turned a tool description into a tuple. Use one plain string |

## Safety notes

- **Read-only by design.** The OAuth scope is `gmail.readonly`.
- **Prompt injection.** Emails are written by strangers and can contain text like
  "ignore your instructions". The system prompt tells the model to treat email
  content as data, never commands. Test this by emailing yourself such a message
  and asking the agent to summarize it.
- **Limits.** `max_steps`, `max_results`, `max_chars`, and `MAX_TOOL_CHARS` stop
  runaway loops and huge token use.
- **The web UI** uses `textContent`, not `innerHTML`, so email text cannot inject
  HTML or scripts into the page.

## Roadmap

1. Read-only agent (done)
2. Reversible actions: labels and drafts, with an Approve / Reject step in the UI
3. Saved state so processed emails are not repeated
4. A scheduler for automatic digests
5. Evaluation set of real emails to measure accuracy
6. Optional: wrap the tools in an MCP server so other clients can reuse them

Anything irreversible (send, delete, forward) should always require human approval.