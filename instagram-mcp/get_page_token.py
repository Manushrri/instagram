#!/usr/bin/env python3
"""
Helper script to get Page Access Token from an existing User Access Token.
This is needed for Instagram Conversations API which requires a Page Access Token.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Import token storage functions
sys.path.insert(0, script_dir)
from instagram_mcp_server import (
    _get_page_access_token_from_user_token,
    _save_tokens,
    _load_tokens,
    get_access_token
)

def main():
    """Get Page Access Token from User Access Token."""
    print(f"\n{'='*60}")
    print("Get Page Access Token")
    print(f"{'='*60}\n")
    
    # Try to get access token from various sources
    try:
        user_token = get_access_token()
        print(f"✅ Found User Access Token\n")
    except Exception as e:
        print(f"❌ Error: Could not get access token: {e}")
        print("\nMake sure you have:")
        print("  - INSTAGRAM_ACCESS_TOKEN set in .env, OR")
        print("  - Completed OAuth setup (run: uv run instagram-mcp/oauth_setup.py)")
        sys.exit(1)
    
    # Get Page Access Token
    print("Fetching Page Access Token from Facebook Pages...")
    try:
        page_info = _get_page_access_token_from_user_token(user_token)
        
        if not page_info:
            print("\n❌ Could not get Page Access Token.")
            print("\nPossible reasons:")
            print("  1. Your access token doesn't have 'pages_show_list' permission")
            print("  2. You don't have any Facebook Pages")
            print("  3. Your Instagram account is not connected to a Facebook Page")
            print("\nTo fix:")
            print("  1. Go to Facebook Developers → Your App → Permissions")
            print("  2. Add 'pages_show_list' permission")
            print("  3. Re-authenticate to get a new token with this permission")
            sys.exit(1)
        
        page_id = page_info.get("page_id")
        page_token = page_info.get("page_access_token")
        ig_user_id = page_info.get("instagram_user_id")
        
        if not page_token:
            print("\n❌ Could not get Page Access Token from Facebook Pages.")
            sys.exit(1)
        
        print(f"\n✅ Successfully retrieved Page Access Token!\n")
        print(f"{'='*60}")
        print("Page Information:")
        print(f"{'='*60}")
        print(f"Facebook Page ID: {page_id}")
        print(f"Page Access Token: {page_token[:20]}...")
        if ig_user_id:
            print(f"Instagram User ID: {ig_user_id}")
        print(f"{'='*60}\n")
        
        # Save to token storage
        tokens_to_save = {
            "page_access_token": page_token,
            "facebook_page_id": page_id
        }
        if ig_user_id:
            tokens_to_save["instagram_user_id"] = ig_user_id
        
        _save_tokens(tokens_to_save)
        
        # Also set environment variables
        os.environ["INSTAGRAM_PAGE_ACCESS_TOKEN"] = page_token
        os.environ["FACEBOOK_PAGE_ID"] = page_id
        
        print("✅ Page Access Token saved to:")
        print(f"   - .instagram_tokens.json")
        print(f"   - Environment variables (INSTAGRAM_PAGE_ACCESS_TOKEN, FACEBOOK_PAGE_ID)")
        print("\n🎉 You can now use Instagram Conversations API!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


