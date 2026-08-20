"""
Gmail OAuth Re-Authentication Helper

Run this script locally to complete Google OAuth authentication.
It will generate `token.json` and output the compact JSON format
to copy into your Hugging Face Space secret GMAIL_TOKEN_DATA.

Usage:
    python authenticate_gmail.py
"""

import os
import json
import sys

def main():
    credentials_path = os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json")
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "token.json")
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    print("=" * 70)
    print("🔑 Gmail OAuth Re-Authentication Helper")
    print("=" * 70)

    if not os.path.exists(credentials_path):
        print(f"❌ Error: Credentials file '{credentials_path}' not found in current directory.")
        print("Please ensure credentials.json is present.")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials

        print(f"\n1. Loading client secrets from '{credentials_path}'...")
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        
        print("2. Opening browser for Google OAuth authorization...")
        print("   (Please select your Gmail account and click 'Allow')")
        creds = flow.run_local_server(port=0)

        print(f"\n3. Saving token to '{token_path}'...")
        token_json_str = creds.to_json()
        with open(token_path, 'w') as token_file:
            token_file.write(token_json_str)
        print("✅ Saved local token.json successfully!")

        # Format for Hugging Face secret (single-line compact JSON)
        token_info = json.loads(token_json_str)
        compact_json = json.dumps(token_info)

        print("\n" + "=" * 70)
        print("📋 ACTION REQUIRED FOR HUGGING FACE SPACE:")
        print("=" * 70)
        print("Copy the following JSON string and update your Hugging Face secret:")
        print("Secret Name : GMAIL_TOKEN_DATA")
        print("Secret Value:\n")
        print(compact_json)
        print("\n" + "=" * 70)
        print("After updating the GMAIL_TOKEN_DATA secret on Hugging Face:")
        print("--> Restart your Hugging Face Space!")
        print("=" * 70 + "\n")

    except ImportError:
        print("❌ Error: google-auth-oauthlib or google-api-python-client is not installed.")
        print("Please run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        sys.exit(1)
    except Exception as e:
        print(f"❌ OAuth Authentication failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
