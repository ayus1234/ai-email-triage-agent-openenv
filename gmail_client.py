"""
Gmail API Client — Real email integration with simulated fallback.
"""

import os
import base64
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class GmailEmail:
    """Represents an email fetched from Gmail or simulation."""
    id: str
    sender: str
    subject: str
    body: str
    folder: str = "INBOX"
    timestamp: str = ""
    is_real: bool = False


class GmailFetcher:
    """Gmail API client with graceful fallback to simulated emails."""

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json")
        self.token_path = os.environ.get("GMAIL_TOKEN_PATH", "token.json")
        self._service = None
        self._is_authenticated = False
        self._try_authenticate()

    @property
    def is_authenticated(self) -> bool:
        return self._is_authenticated

    def _try_authenticate(self):
        """Attempt Gmail API authentication. Fail silently if not available."""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
                       'https://www.googleapis.com/auth/gmail.modify']
            creds = None
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif os.path.exists(self.credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(self.token_path, 'w') as token:
                        token.write(creds.to_json())
                else:
                    print("[GmailFetcher] No credentials found — using simulated mode", flush=True)
                    return
            self._service = build('gmail', 'v1', credentials=creds)
            self._is_authenticated = True
            print("[GmailFetcher] ✅ Gmail API authenticated", flush=True)
        except ImportError:
            print("[GmailFetcher] Google API libs not installed — simulated mode", flush=True)
        except Exception as e:
            print(f"[GmailFetcher] Auth failed: {e} — simulated mode", flush=True)

    def fetch_inbox(self, max_results: int = 10) -> List[GmailEmail]:
        """Fetch real emails from Gmail inbox."""
        if not self._is_authenticated or not self._service:
            return self.get_simulated_emails()
        try:
            results = self._service.users().messages().list(
                userId='me', maxResults=max_results, labelIds=['INBOX']).execute()
            messages = results.get('messages', [])
            emails = []
            for msg_data in messages:
                msg = self._service.users().messages().get(
                    userId='me', id=msg_data['id'], format='full').execute()
                headers = {h['name']: h['value'] for h in msg['payload']['headers']}
                body = self._extract_body(msg['payload'])
                emails.append(GmailEmail(
                    id=msg_data['id'], sender=headers.get('From', 'unknown'),
                    subject=headers.get('Subject', '(no subject)'),
                    body=body[:500], folder="INBOX",
                    timestamp=headers.get('Date', ''), is_real=True))
            return emails
        except Exception as e:
            print(f"[GmailFetcher] Fetch error: {e}", flush=True)
            return self.get_simulated_emails()

    def _extract_body(self, payload: dict) -> str:
        if payload.get('body', {}).get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
        for part in payload.get('parts', []):
            if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
        return "(could not extract body)"

    @staticmethod
    def get_simulated_emails(task_name: str = "mixed") -> List[GmailEmail]:
        """Enhanced simulated emails for demo."""
        sets = {
            "easy": [
                GmailEmail(id="e1", sender="boss@company.com", subject="Project update",
                          body="Please send the latest report by end of day.", folder="INBOX"),
                GmailEmail(id="e2", sender="scam@spam.com", subject="You won a lottery!",
                          body="Click here to claim $1M. Act NOW!", folder="INBOX"),
                GmailEmail(id="e3", sender="colleague@company.com", subject="Lunch?",
                          body="Are we still on for lunch at 12:30?", folder="INBOX"),
            ],
            "medium": [
                GmailEmail(id="e1", sender="deals@cheapmeds.xyz", subject="URGENT: Limited offer!",
                          body="Buy medications at 90% OFF! No prescription needed!", folder="INBOX"),
                GmailEmail(id="e2", sender="sarah.johnson@gmail.com", subject="Refund request - Order #123",
                          body="Hi, I would like a refund for order #123. Wrong item received.", folder="INBOX"),
            ],
            "hard": [
                GmailEmail(id="e1", sender="promo@winbig-now.com", subject="Your exclusive reward",
                          body="You have been chosen! Verify identity to receive $5,000.", folder="INBOX"),
                GmailEmail(id="e2", sender="mark.chen@outlook.com", subject="Refund - Defective Product",
                          body="Order #456 stopped working after 2 days. I want a full refund.", folder="INBOX"),
                GmailEmail(id="e3", sender="accounts@vendor-corp.com", subject="Invoice #789",
                          body="Invoice #789 for consulting: $4,750.00. Net 30 terms.", folder="INBOX"),
            ],
        }
        sets["mixed"] = sets["easy"] + [sets["medium"][1]]
        return sets.get(task_name, sets["mixed"])
