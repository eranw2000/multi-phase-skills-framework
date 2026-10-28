#!/usr/bin/env python3
"""One-time consent: mint an OAuth token that can read and write Google Sheets.

Run this once, in a terminal, on the machine whose browser you can click in. It opens
a Google consent page, and on approval it writes the refresh token to

    $PLAN_STATUS_GOOGLE_DIR/sheets_token.json   (default ~/.config/plan-status-sheet)

next to the OAuth client file, credentials.json, which you download once from the
Google Cloud console (see SKILL.md, "Google sign-in, once per machine").

The scope is deliberately NARROW. `spreadsheets` alone can create a spreadsheet and
read and write any spreadsheet this account can already open. It cannot read the rest
of Drive, and it cannot change sharing. Widening a scope later is not free: a token's
scopes are fixed at consent time, so a wider list would need this run again.
"""
import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

GOOGLE_DIR = os.path.expanduser(os.environ.get("PLAN_STATUS_GOOGLE_DIR")
                                or "~/.config/plan-status-sheet")
CREDENTIALS = os.path.join(GOOGLE_DIR, "credentials.json")
TOKEN = os.path.join(GOOGLE_DIR, "sheets_token.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main() -> None:
    if not os.path.isfile(CREDENTIALS):
        sys.exit(f"no OAuth client at {CREDENTIALS}. Create a Desktop app OAuth client "
                 f"in the Google Cloud console and save its JSON file there "
                 f"(SKILL.md, \"Google sign-in, once per machine\").")
    if os.path.isfile(TOKEN) and "--force" not in sys.argv:
        # Refusing beats overwriting. A working token is the thing this script exists to
        # produce, and a re-consent that fails halfway would leave nothing in its place.
        existing = json.load(open(TOKEN))
        sys.exit(f"{TOKEN} already exists, scopes {existing.get('scopes')}. "
                 f"Pass --force to replace it.")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    with open(TOKEN, "w") as handle:
        handle.write(creds.to_json())
    os.chmod(TOKEN, 0o600)

    # Print metadata only. A token file's contents never go to a terminal or a log.
    written = json.load(open(TOKEN))
    print(f"wrote {TOKEN}")
    print(f"granted scopes: {written.get('scopes')}")
    print(f"refresh token present: {bool(written.get('refresh_token'))}")


if __name__ == "__main__":
    main()
