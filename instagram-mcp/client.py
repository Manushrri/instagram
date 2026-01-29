"""
Instagram API Client

Singleton client that handles all Instagram Graph API operations.
"""

import os
import json
import time
import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger("instagram.client")


class InstagramClient:
    """Client for Instagram Graph API operations."""
    
    def __init__(self, settings: "Settings", token_provider=None):
        """
        Initialize the Instagram client.
        
        Args:
            settings: Configuration settings
            token_provider: Optional callable that returns credentials
        """
        self.settings = settings
        self.token_provider = token_provider
        self._token_cache: Dict[str, Any] = {}
        
        logger.info("InstagramClient initialized")
    
    def _get_token_storage_path(self) -> Path:
        """Get the path to the token storage file."""
        return Path(__file__).parent / '.instagram_tokens.json'
    
    def _load_tokens(self) -> Dict[str, Any]:
        """Load tokens from persistent storage."""
        token_file = self._get_token_storage_path()
        if token_file.exists():
            try:
                with open(token_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load tokens: {e}")
        return {}
    
    def _save_tokens(self, tokens: Dict[str, Any]) -> None:
        """Save tokens to persistent storage."""
        token_file = self._get_token_storage_path()
        existing = self._load_tokens()
        existing.update(tokens)
        existing["access_token_saved_at"] = time.time()
        
        with open(token_file, 'w') as f:
            json.dump(existing, f, indent=2)
        
        logger.info("Tokens saved to storage")
    
    def _is_token_expired(self) -> bool:
        """Check if the stored access token is expired."""
        stored_tokens = self._load_tokens()
        expires_in = stored_tokens.get("expires_in")
        saved_at = stored_tokens.get("access_token_saved_at")
        
        if not expires_in or not saved_at:
            return False
        
        current_time = time.time()
        expiry_time = saved_at + expires_in
        buffer = 300  # 5 minutes buffer
        
        return current_time >= (expiry_time - buffer)
    
    def _refresh_token(self, refresh_token: str) -> Optional[str]:
        """Refresh the access token."""
        if not self.settings.oauth2_client_id or not self.settings.oauth2_client_secret:
            return None
        
        token_url = f"https://graph.facebook.com/{self.settings.graph_api_version}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.settings.oauth2_client_id,
            "client_secret": self.settings.oauth2_client_secret,
            "fb_exchange_token": refresh_token
        }
        
        try:
            response = requests.get(token_url, params=params, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            if "access_token" in token_data:
                tokens_to_save = {
                    "access_token": token_data["access_token"],
                    "expires_in": token_data.get("expires_in", 5184000)
                }
                
                existing = self._load_tokens()
                if existing.get("refresh_token"):
                    tokens_to_save["refresh_token"] = existing["refresh_token"]
                
                self._save_tokens(tokens_to_save)
                logger.info("Token refreshed successfully")
                return token_data["access_token"]
                
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
        
        return None
    
    def get_access_token(self) -> str:
        """Get Instagram access token."""
        # Check token provider first (for backend integration)
        if self.token_provider:
            try:
                creds = self.token_provider()
                if creds and creds.get("access_token"):
                    return creds["access_token"]
            except Exception as e:
                logger.warning(f"Token provider failed: {e}")
        
        # Direct token from environment
        direct_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        if direct_token:
            return direct_token
        
        # Load from persistent storage
        stored_tokens = self._load_tokens()
        stored_access_token = stored_tokens.get("access_token")
        
        if stored_access_token:
            if self._is_token_expired():
                refresh_token = stored_tokens.get("refresh_token") or stored_access_token
                if refresh_token:
                    new_token = self._refresh_token(refresh_token)
                    if new_token:
                        return new_token
            return stored_access_token
        
        # OAuth2 token from environment
        oauth_token = os.getenv("INSTAGRAM_OAUTH_ACCESS_TOKEN")
        if oauth_token:
            return oauth_token
        
        raise RuntimeError("Missing access token. Run: uv run instagram-mcp/oauth_setup.py")
    
    def get_base_url(self) -> str:
        """Get Instagram Graph API base URL."""
        return f"https://graph.facebook.com/{self.settings.graph_api_version}"
    
    def make_api_request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make a request to Instagram Graph API."""
        access_token = self.get_access_token()
        url = f"{self.get_base_url()}/{endpoint.lstrip('/')}"
        
        if params is None:
            params = {}
        params["access_token"] = access_token
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, params=params, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    pass
            raise Exception(f"API request failed: {error_msg}")
    
    def get_instagram_user_id(self, provided_id: Optional[str] = None) -> str:
        """Auto-detect Instagram user ID."""
        if provided_id:
            return provided_id
        
        env_id = os.getenv("INSTAGRAM_USER_ID")
        if env_id:
            return env_id
        
        stored = self._load_tokens()
        if stored.get("instagram_user_id"):
            return stored["instagram_user_id"]
        
        # Auto-detect from API
        try:
            response = self.make_api_request(
                "GET", "me/accounts", 
                params={"fields": "instagram_business_account"}
            )
            for page in response.get("data", []):
                ig_account = page.get("instagram_business_account", {})
                if ig_account.get("id"):
                    self._save_tokens({"instagram_user_id": ig_account["id"]})
                    return ig_account["id"]
        except Exception as e:
            logger.warning(f"Auto-detect user ID failed: {e}")
        
        raise ValueError(
            "Could not auto-detect Instagram user ID. "
            "Set INSTAGRAM_USER_ID environment variable."
        )
    
    def get_page_for_ig_account(self, ig_user_id: str) -> Dict[str, Optional[str]]:
        """Get Facebook Page ID and Page Access Token for Instagram account."""
        stored = self._load_tokens()
        
        result = {
            "page_id": stored.get("facebook_page_id") or os.getenv("FACEBOOK_PAGE_ID"),
            "page_access_token": stored.get("page_access_token") or os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN")
        }
        
        if result["page_id"] and result["page_access_token"]:
            return result
        
        # Try to auto-detect
        try:
            response = self.make_api_request(
                "GET", "me/accounts",
                params={"fields": "id,access_token,instagram_business_account"}
            )
            for page in response.get("data", []):
                ig_account = page.get("instagram_business_account", {})
                if ig_account.get("id") == ig_user_id:
                    result["page_id"] = page.get("id")
                    result["page_access_token"] = page.get("access_token")
                    self._save_tokens({
                        "facebook_page_id": result["page_id"],
                        "page_access_token": result["page_access_token"]
                    })
                    return result
        except Exception as e:
            logger.warning(f"Auto-detect page info failed: {e}")
        
        return result
    
    def load_tokens(self) -> Dict[str, Any]:
        """Public method to load tokens (for messaging tools)."""
        return self._load_tokens()

