# auth.py
# ---------------------------------------------------------------------------
# Handles Gmail login using OAuth 2.0. It uses a read-only scope, so the
# program cannot send or delete email.
#
# Why OAuth instead of a password? Your script never sees your Google
# password. You approve access in Google's own page, and Google hands the
# script a limited-permission token instead.
# ---------------------------------------------------------------------------

"""
GMAIL AUTHENTICATION (OAuth 2.0)

This function authenticates a Python application with the Gmail API.

1. SCOPES:
   Requests gmail.readonly permission, allowing the app to read emails
   but not send, delete, or modify them.

2. token.json:
   Checks whether previously saved authentication credentials exist.
   If they exist, loads them to avoid logging in every time.

3. TOKEN REFRESH:
   If the access token has expired and a refresh token is available,
   automatically requests a new access token.

4. OAUTH LOGIN:
   If valid credentials are unavailable, opens a Google login page
   using credentials.json and asks the user to authorize the app.

5. SAVE CREDENTIALS:
   Saves the authentication tokens in token.json for future use.

6. BUILD SERVICE:
   Uses Google's build() function to create and return a Gmail API
   service object, which can then be used to read and retrieve emails.

FILES REQUIRED:
- credentials.json: Google OAuth client credentials.
- token.json: Automatically generated authentication tokens.

NOTE: Never upload credentials.json or token.json to public GitHub.
"""

import os                                                   # to check whether token.json exists
from google.auth.transport.requests import Request         # used to ask Google for a fresh token
from google.oauth2.credentials import Credentials           # holds the login tokens
from google_auth_oauthlib.flow import InstalledAppFlow      # runs the browser login for desktop apps
from googleapiclient.discovery import build                 # builds the Gmail API handle

# SCOPES = the list of permissions the app asks for.
# "gmail.readonly" means: read email, nothing else. This is the strongest
# safety feature in the project, because even buggy code or a tricked AI
# model physically cannot send or delete mail with this permission.
# If you ever change this list (for example to add labels in Stage 4),
# delete token.json so Google asks you to approve the new permissions.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    """Log in to Gmail (or reuse a saved login) and return the API handle."""

    creds = None   # "creds" will hold our login tokens; None means "not loaded yet"

    # STEP 1: Reuse a previous login if one was saved.
    # token.json is created automatically the first time you log in.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # STEP 2: If there are no credentials, or they aren't valid, fix that.
    # "valid" means the access token exists and hasn't expired.
    if not creds or not creds.valid:

        # Case A: the token expired, but we hold a refresh token.
        # The refresh token lets us get a new access token silently,
        # with no browser and no clicking.
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # Case B: no usable credentials at all (first run, or token.json deleted).
        # Open the browser so you can log in and approve access.
        else:
            # Reads your app's identity from credentials.json
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            # Starts a tiny local web server to catch Google's response.
            # port=0 means "pick any free port", which avoids conflicts.
            creds = flow.run_local_server(port=0)

        # STEP 3: Save the (new or refreshed) tokens so next time we skip the login.
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    # STEP 4: Build and return the Gmail API handle.
    # "gmail" = which API, "v1" = which version. Every Gmail call in
    # gmail_tools.py goes through the object returned here.
    return build("gmail", "v1", credentials=creds)