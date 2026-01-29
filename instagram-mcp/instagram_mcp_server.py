import os
import json
import argparse
import time
import requests
from typing import Optional, List, Dict, Any, Annotated
from urllib.parse import urlencode, parse_qs, urlparse
from dotenv import load_dotenv
try:
    # Prefer the standalone fastmcp package
    from fastmcp import FastMCP
except Exception:
    # Fallback to the namespaced import if available
    from mcp.server.fastmcp import FastMCP

# Load .env file automatically from the same directory as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"Loaded environment variables from: {env_path}")
else:
    print(f"Warning: .env file not found at: {env_path}")

def get_env(var: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch environment variable or return default if missing."""
    value = os.getenv(var)
    if not value and default is not None:
        return default
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var}")
    return value

def get_access_token() -> str:
    """Get Instagram access token from environment, persistent storage, or OAuth2."""
    # First try direct access token from environment
    direct_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if direct_token:
        return direct_token
    
    # Try to load from persistent storage
    stored_tokens = _load_tokens()
    stored_access_token = stored_tokens.get("access_token")
    
    # Check if token from storage is expired
    if stored_access_token:
        if _is_token_expired():
            # Try to refresh the token
            refresh_token = stored_tokens.get("refresh_token") or os.getenv("INSTAGRAM_OAUTH_REFRESH_TOKEN")
            if refresh_token and _is_oauth2_enabled():
                try:
                    new_token = _refresh_oauth2_token(refresh_token)
                    if new_token:
                        return new_token
                    else:
                        print("Warning: Failed to refresh expired token, using stored token anyway")
                except Exception as e:
                    print(f"Warning: Failed to refresh OAuth2 token: {e}, using stored token anyway")
        return stored_access_token
    
    # Try OAuth2 token from environment (backward compatibility)
    oauth_token = os.getenv("INSTAGRAM_OAUTH_ACCESS_TOKEN")
    if oauth_token:
        return oauth_token
    
    # If using OAuth2, check if we need to refresh
    if _is_oauth2_enabled():
        oauth_refresh_token = os.getenv("INSTAGRAM_OAUTH_REFRESH_TOKEN")
        if oauth_refresh_token:
            # Try to refresh the token
            try:
                new_token = _refresh_oauth2_token(oauth_refresh_token)
                if new_token:
                    return new_token
            except Exception as e:
                print(f"Warning: Failed to refresh OAuth2 token: {e}")
    
    raise RuntimeError("Missing required access token. Set INSTAGRAM_ACCESS_TOKEN or configure OAuth2.")

def get_graph_api_version() -> str:
    """Get Graph API version from environment or use default."""
    return get_env("INSTAGRAM_GRAPH_API_VERSION", "v21.0")

def get_base_url() -> str:
    """Get Instagram Graph API base URL."""
    version = get_graph_api_version()
    return f"https://graph.facebook.com/{version}"

# -------------------- TOKEN STORAGE FUNCTIONS --------------------

def _get_token_storage_path() -> str:
    """Get the path to the token storage file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, '.instagram_tokens.json')

def _load_tokens() -> Dict[str, Any]:
    """Load tokens from persistent storage."""
    token_file = _get_token_storage_path()
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load tokens from {token_file}: {e}")
            return {}
    return {}

def _save_tokens(tokens: Dict[str, Any]) -> None:
    """Save tokens to persistent storage."""
    token_file = _get_token_storage_path()
    try:
        # Load existing tokens to preserve other fields
        existing_tokens = _load_tokens()
        existing_tokens.update(tokens)
        
        # Add timestamp for expiration tracking
        if "access_token" in tokens:
            existing_tokens["access_token"] = tokens["access_token"]
            existing_tokens["access_token_saved_at"] = time.time()
            if "expires_in" in tokens:
                existing_tokens["expires_in"] = tokens["expires_in"]
        
        if "refresh_token" in tokens:
            existing_tokens["refresh_token"] = tokens["refresh_token"]
        
        # Save to file
        with open(token_file, 'w') as f:
            json.dump(existing_tokens, f, indent=2)
        
        # Also update environment variables for backward compatibility
        if "access_token" in tokens:
            os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = tokens["access_token"]
        if "refresh_token" in tokens:
            os.environ["INSTAGRAM_OAUTH_REFRESH_TOKEN"] = tokens["refresh_token"]
        if "page_access_token" in tokens:
            os.environ["INSTAGRAM_PAGE_ACCESS_TOKEN"] = tokens["page_access_token"]
        if "facebook_page_id" in tokens:
            os.environ["FACEBOOK_PAGE_ID"] = tokens["facebook_page_id"]
            
    except IOError as e:
        print(f"Warning: Failed to save tokens to {token_file}: {e}")

def _is_token_expired() -> bool:
    """Check if the stored access token is expired or will expire soon (within 1 day)."""
    tokens = _load_tokens()
    if "access_token_saved_at" not in tokens or "expires_in" not in tokens:
        return False  # Can't determine, assume valid
    
    saved_at = tokens["access_token_saved_at"]
    expires_in = tokens["expires_in"]
    current_time = time.time()
    
    # Check if token expires within 1 day (86400 seconds = 24 hours)
    # This ensures the token is refreshed 1 day before it actually expires
    time_until_expiry = (saved_at + expires_in) - current_time
    return time_until_expiry < 86400

# -------------------- OAUTH2 FUNCTIONS --------------------

def _is_oauth2_enabled() -> bool:
    """Check if OAuth2 is enabled."""
    return bool(os.getenv("OAUTH2_CLIENT_ID") and os.getenv("OAUTH2_CLIENT_SECRET"))

def _get_oauth2_config() -> Dict[str, str]:
    """Get OAuth2 configuration from environment."""
    # Default to localhost callback for automated setup, but allow override
    default_redirect_uri = os.getenv("OAUTH2_REDIRECT_URI", "http://localhost:8080/callback")
    return {
        "client_id": os.getenv("OAUTH2_CLIENT_ID", ""),
        "client_secret": os.getenv("OAUTH2_CLIENT_SECRET", ""),
        "redirect_uri": default_redirect_uri,
        "scopes": os.getenv("OAUTH2_SCOPES", "email,manage_fundraisers,publish_video,catalog_management,pages_show_list,ads_management,ads_read,business_management,pages_messaging,instagram_basic,instagram_manage_comments,instagram_manage_insights,instagram_content_publish,leads_retrieval,whatsapp_business_management,instagram_manage_messages,pages_read_engagement,pages_manage_metadata,pages_manage_ads,whatsapp_business_messaging,instagram_shopping_tag_products,instagram_branded_content_brand,instagram_branded_content_creator,instagram_branded_content_ads_brand,instagram_manage_upcoming_events,instagram_creator_marketplace_discovery,instagram_manage_contents")
    }

def _get_oauth2_authorization_url(state: Optional[str] = None) -> str:
    """Generate OAuth2 authorization URL."""
    config = _get_oauth2_config()
    
    if not config["client_id"]:
        raise ValueError("OAUTH2_CLIENT_ID is required for OAuth2")
    
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "scope": config["scopes"],
        "response_type": "code"
    }
    
    if state:
        params["state"] = state
    
    # Instagram/Facebook OAuth2 endpoint
    base_url = "https://www.facebook.com/v21.0/dialog/oauth"
    return f"{base_url}?{urlencode(params)}"

def _exchange_oauth2_code(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access token via Composio backend."""
    config = _get_oauth2_config()
    
    if not config["client_id"] or not config["client_secret"]:
        raise ValueError("OAUTH2_CLIENT_ID and OAUTH2_CLIENT_SECRET are required")
    
    # Use Facebook's token endpoint directly
    token_url = "https://graph.facebook.com/v21.0/oauth/access_token"
    
    params = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "redirect_uri": config["redirect_uri"],
        "code": code
    }
    
    try:
        response = requests.post(token_url, params=params, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        
        short_lived_token = token_data.get("access_token")
        
        # Step 2: Exchange short-lived token for long-lived token (60 days)
        # This gives us expires_in!
        if short_lived_token:
            print("Exchanging short-lived token for long-lived token...")
            long_lived_params = {
                "grant_type": "fb_exchange_token",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "fb_exchange_token": short_lived_token
            }
            
            try:
                long_lived_response = requests.get(token_url, params=long_lived_params, timeout=30)
                long_lived_response.raise_for_status()
                long_lived_data = long_lived_response.json()
                
                # Debug: print what Facebook returned
                print(f"Long-lived token response keys: {list(long_lived_data.keys())}")
                
                # Use the long-lived token instead
                if "access_token" in long_lived_data:
                    token_data["access_token"] = long_lived_data["access_token"]
                    print("Successfully obtained long-lived token")
                
                # Long-lived token response includes expires_in
                if "expires_in" in long_lived_data:
                    token_data["expires_in"] = long_lived_data["expires_in"]
                    print(f"Token expires in: {long_lived_data['expires_in']} seconds (~{long_lived_data['expires_in'] // 86400} days)")
                else:
                    # Facebook long-lived tokens are valid for 60 days
                    # Set default if not returned by API
                    token_data["expires_in"] = 5184000  # 60 days in seconds
                    print("Note: Facebook did not return expires_in, using default of 60 days for long-lived token")
                    
            except Exception as e:
                print(f"Warning: Could not exchange for long-lived token: {e}")
                print("Using short-lived token instead (valid for ~1-2 hours)")
                # Set a default expires_in for short-lived token
                if "expires_in" not in token_data:
                    token_data["expires_in"] = 3600  # 1 hour default for short-lived
        
        # Store tokens in persistent storage and environment
        tokens_to_save = {}
        if "access_token" in token_data:
            tokens_to_save["access_token"] = token_data["access_token"]
            os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = token_data["access_token"]
        
        if "refresh_token" in token_data:
            tokens_to_save["refresh_token"] = token_data["refresh_token"]
            os.environ["INSTAGRAM_OAUTH_REFRESH_TOKEN"] = token_data["refresh_token"]
        
        if "expires_in" in token_data:
            tokens_to_save["expires_in"] = token_data["expires_in"]
        
        # Save to persistent storage
        if tokens_to_save:
            _save_tokens(tokens_to_save)
            print("Tokens saved to persistent storage automatically")
        
        # Try to get Page Access Token automatically
        if "access_token" in token_data:
            try:
                page_token_info = _get_page_access_token_from_user_token(token_data["access_token"])
                if page_token_info:
                    tokens_to_save["page_access_token"] = page_token_info.get("page_access_token")
                    tokens_to_save["facebook_page_id"] = page_token_info.get("page_id")
                    if tokens_to_save.get("page_access_token"):
                        os.environ["INSTAGRAM_PAGE_ACCESS_TOKEN"] = tokens_to_save["page_access_token"]
                    if tokens_to_save.get("facebook_page_id"):
                        os.environ["FACEBOOK_PAGE_ID"] = tokens_to_save["facebook_page_id"]
                    _save_tokens(tokens_to_save)
                    print("Page Access Token automatically retrieved and saved")
            except Exception as e:
                print(f"Warning: Could not automatically get Page Access Token: {e}")
                print("   You may need to set INSTAGRAM_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID manually")
        
        return token_data
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except:
                pass
        raise Exception(f"Failed to exchange OAuth2 code: {error_msg}")

def _refresh_oauth2_token(refresh_token: str) -> Optional[str]:
    """Refresh OAuth2 access token."""
    config = _get_oauth2_config()
    
    if not config["client_id"] or not config["client_secret"]:
        return None
    
    token_url = "https://graph.facebook.com/v21.0/oauth/access_token"
    
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "fb_exchange_token": refresh_token
    }
    
    try:
        response = requests.get(token_url, params=params, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        
        if "access_token" in token_data:
            # Load existing tokens to preserve refresh_token
            existing_tokens = _load_tokens()
            
            # Save refreshed token to persistent storage
            tokens_to_save = {
                "access_token": token_data["access_token"]
            }
            if "expires_in" in token_data:
                tokens_to_save["expires_in"] = token_data["expires_in"]
            
            # Preserve existing refresh_token, or save new one if Facebook returns it
            if "refresh_token" in token_data:
                tokens_to_save["refresh_token"] = token_data["refresh_token"]
            elif existing_tokens.get("refresh_token"):
                # Keep the existing refresh_token if Facebook didn't return a new one
                tokens_to_save["refresh_token"] = existing_tokens["refresh_token"]
            
            # Try to refresh Page Access Token as well
            try:
                page_token_info = _get_page_access_token_from_user_token(token_data["access_token"])
                if page_token_info:
                    tokens_to_save["page_access_token"] = page_token_info.get("page_access_token")
                    tokens_to_save["facebook_page_id"] = page_token_info.get("page_id")
            except Exception as e:
                print(f"Warning: Could not refresh Page Access Token: {e}")
            
            _save_tokens(tokens_to_save)
            os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = token_data["access_token"]
            if tokens_to_save.get("page_access_token"):
                os.environ["INSTAGRAM_PAGE_ACCESS_TOKEN"] = tokens_to_save["page_access_token"]
            if tokens_to_save.get("facebook_page_id"):
                os.environ["FACEBOOK_PAGE_ID"] = tokens_to_save["facebook_page_id"]
            print("Token refreshed and saved automatically")
            return token_data["access_token"]
        
        return None
    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to refresh token: {e}")
        return None

def make_api_request(method: str, endpoint: str, params: Dict[str, Any] = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to Instagram Graph API."""
    access_token = get_access_token()
    base_url = get_base_url()
    url = f"{base_url}/{endpoint.lstrip('/')}"
    
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

# Initialize MCP server
mcp = FastMCP("instagram-mcp")

def _validate_required(params: Dict[str, Any], required: List[str]):
    """Raise ValueError if any required params are missing/blank.

    Treats empty strings, None, and empty lists as missing.
    """
    missing = []
    for key in required:
        value = params.get(key)
        if value is None:
            missing.append(key)
        elif isinstance(value, str) and value.strip() == "":
            missing.append(key)
        elif isinstance(value, (list, dict)) and len(value) == 0:
            missing.append(key)
    if missing:
        raise ValueError(f"Missing required parameter(s): {', '.join(missing)}")
    return None

def _get_instagram_user_id(provided_id: Optional[str] = None) -> str:
    """Auto-detect Instagram user ID from access token. No env var needed."""
    if provided_id:
        return provided_id
    
    # Check env var first (user can set it explicitly)
    env_user_id = os.getenv("INSTAGRAM_USER_ID")
    if env_user_id:
        return env_user_id
    
    # Auto-detect from access token by querying Facebook Pages
    try:
        accounts = make_api_request(
            "GET",
            "me/accounts",
            params={"fields": "id,instagram_business_account{id,username}"},
        )
        pages_data = accounts.get("data", [])
        
        if not pages_data:
            raise RuntimeError(
                "No Facebook Pages found. To fix this:\n"
                "1. Ensure your access token has 'pages_show_list' permission\n"
                "2. Make sure you have at least one Facebook Page\n"
                "3. Or set INSTAGRAM_USER_ID environment variable directly"
            )
        
        for page in pages_data:
            ig_account = page.get("instagram_business_account")
            if ig_account and ig_account.get("id"):
                return ig_account.get("id")
        
        # No Instagram account found on any page
        raise RuntimeError(
            "No Instagram Business/Creator account found on your Facebook Pages. To fix this:\n"
            "1. Make sure your Instagram account is a Business or Creator account (not Personal)\n"
            "2. Connect your Instagram account to a Facebook Page in Facebook Business Settings\n"
            "3. Or set INSTAGRAM_USER_ID environment variable directly with your Instagram user ID"
        )
    except RuntimeError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # API call failed - provide helpful error
        error_msg = str(e)
        if "permission" in error_msg.lower() or "access" in error_msg.lower():
            raise RuntimeError(
                f"Failed to access Facebook Pages: {error_msg}\n"
                "To fix this:\n"
                "1. Ensure your access token has 'pages_show_list' permission\n"
                "2. Or set INSTAGRAM_USER_ID environment variable directly"
            )
        else:
            raise RuntimeError(
                f"Could not auto-detect Instagram user ID: {error_msg}\n"
                "To fix this:\n"
                "1. Set INSTAGRAM_USER_ID environment variable with your Instagram user ID\n"
                "2. Or ensure your access token has proper permissions and your Instagram account is connected to a Facebook Page"
            )

def _get_page_access_token_from_user_token(user_access_token: str) -> Optional[Dict[str, str]]:
    """Get Page Access Token and Page ID from a User Access Token."""
    try:
        base_url = get_base_url()
        url = f"{base_url}/me/accounts"
        
        params = {
            "access_token": user_access_token,
            "fields": "id,access_token,instagram_business_account{id}"
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        accounts_data = response.json()
        
        pages = accounts_data.get("data", [])
        if not pages:
            return None
        
        # Find the first page with an Instagram account
        for page in pages:
            ig_account = page.get("instagram_business_account")
            if ig_account and ig_account.get("id"):
                return {
                    "page_id": page.get("id"),
                    "page_access_token": page.get("access_token"),
                    "instagram_user_id": ig_account.get("id")
                }
        
        # If no Instagram account found, return the first page anyway (user might connect later)
        if pages:
            return {
                "page_id": pages[0].get("id"),
                "page_access_token": pages[0].get("access_token"),
                "instagram_user_id": None
            }
        
        return None
    except Exception as e:
        print(f"Warning: Failed to get Page Access Token: {e}")
        return None

def _get_page_for_ig_account(ig_user_id: str) -> Dict[str, Optional[str]]:
    """Find the Facebook Page ID and Page Access Token for the given Instagram user ID."""
    # ALWAYS check stored tokens first (they're the most reliable source)
    stored_tokens = _load_tokens()
    stored_page_token = stored_tokens.get("page_access_token")
    stored_page_id = stored_tokens.get("facebook_page_id")
    
    # Use stored tokens if available (they take priority)
    if stored_page_token and stored_page_id:
        # Set in environment for immediate use
        os.environ["INSTAGRAM_PAGE_ACCESS_TOKEN"] = stored_page_token
        os.environ["FACEBOOK_PAGE_ID"] = stored_page_id
        print(f"Loaded Page Access Token from storage (Page ID: {stored_page_id})")
        return {"page_id": stored_page_id, "page_access_token": stored_page_token}
    
    # Fallback to environment variables
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    page_access_token = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN")
    
    # If we have both from env, use them
    if page_access_token and page_id:
        return {"page_id": page_id, "page_access_token": page_access_token}
    
    # If we have partial info, combine env and stored
    if not page_access_token and stored_page_token:
        page_access_token = stored_page_token
        os.environ["INSTAGRAM_PAGE_ACCESS_TOKEN"] = stored_page_token
    if not page_id and stored_page_id:
        page_id = stored_page_id
        os.environ["FACEBOOK_PAGE_ID"] = stored_page_id
    
    # If we now have both, return them
    if page_access_token and page_id:
        return {"page_id": page_id, "page_access_token": page_access_token}
    
    # Only try API auto-detection if we still don't have tokens
    if not page_access_token or not page_id:
        try:
            accounts = make_api_request(
                "GET",
                "me/accounts",
                params={"fields": "id,access_token,instagram_business_account"},
            )
            pages_data = accounts.get("data", [])
            
            for page in pages_data:
                ig_account = page.get("instagram_business_account", {})
                if ig_account and ig_account.get("id") == ig_user_id:
                    page_id = page.get("id")
                    page_access_token = page.get("access_token")
                    break
                # Also check if we have a page_id from env and this is that page
                if page_id and page.get("id") == page_id:
                    page_access_token = page.get("access_token")
        except Exception as e:
            # Log the error but don't fail - let caller handle missing page_id
            print(f"Warning: Could not auto-detect Facebook Page: {e}")

    return {"page_id": page_id, "page_access_token": page_access_token}

# -------------------- TOOLS --------------------

@mcp.tool(
    "CREATE_MEDIA_CONTAINER",
    description="Create Media Container. Create a draft media container for photos/videos/reels before publishing. PARAMETERS: image_url OR video_url (one required) - Public URL of media. caption (optional) - Post caption. media_type (optional) - 'IMAGE' or 'VIDEO'. cover_url (optional) - Cover image for videos. is_carousel_item (optional) - True if part of carousel. RETURNS: 'id' field (creation_id) - USE THIS IN: GET_POST_STATUS (to check processing), CREATE_POST or POST_IG_USER_MEDIA_PUBLISH (to publish). WORKFLOW: 1) Call this → 2) Get 'id' → 3) Call GET_POST_STATUS until 'FINISHED' → 4) Call CREATE_POST with creation_id.",
)
def INSTAGRAM_CREATE_MEDIA_CONTAINER(
    image_url: Annotated[Optional[str], "Image URL for photo post"] = None,
    video_url: Annotated[Optional[str], "Video URL for video/reel post"] = None,
    caption: Annotated[Optional[str], "Caption for the media"] = None,
    media_type: Annotated[Optional[str], "Media type (IMAGE or VIDEO only - API only accepts these two)"] = None,
    content_type: Annotated[Optional[str], "Content type (optional)"] = None,
    cover_url: Annotated[Optional[str], "Cover image URL for video/reel (optional)"] = None,
    is_carousel_item: Annotated[Optional[bool], "Set True if this media is part of a carousel"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Create a draft media container for photos/videos/reels before publishing."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        # Validate that either image_url or video_url is provided
        if not image_url and not video_url:
            raise ValueError("Either image_url or video_url must be provided")
        
        # Determine media type if not provided
        if not media_type:
            if video_url:
                media_type = "VIDEO"  # Default to VIDEO for videos
            elif image_url:
                media_type = "IMAGE"
        else:
            # Normalize media_type to uppercase
            media_type = media_type.upper()
            # Validate media_type
            if media_type not in ["IMAGE", "VIDEO"]:
                raise ValueError(f"media_type must be 'IMAGE' or 'VIDEO', not '{media_type}'. For Reels, use media_type='VIDEO' with is_reel=True.")
        
        # Validate media_type matches provided URLs
        if media_type == "IMAGE" and not image_url:
            raise ValueError("media_type='IMAGE' requires image_url")
        if media_type == "VIDEO" and not video_url:
            raise ValueError("media_type='VIDEO' requires video_url")
        
        # Build params - only include non-empty values
        params = {
            "media_type": media_type,
        }
        
        if image_url:
            params["image_url"] = image_url
        if video_url:
            params["video_url"] = video_url

        if content_type:
            params["content_type"] = content_type
        if cover_url:
            params["cover_url"] = cover_url
        if is_carousel_item is True:
            params["is_carousel_item"] = True
        
        if caption:
            params["caption"] = caption
        
        if graph_api_version:
            # Temporarily override version for this request
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", f"{ig_user_id}/media", data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", f"{ig_user_id}/media", data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to create media container: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "POST_IG_USER_MEDIA",
    description="Post IG User Media. Tool to create a media container for Instagram posts. Use this to create a container for images, videos, Reels, or carousels. Returns a 'id' field (creation_id) that you must use in CREATE_POST, POST_IG_USER_MEDIA_PUBLISH, or GET_POST_STATUS. This is the first step in Instagram's two-step publishing process - after creating the container, use CREATE_POST or POST_IG_USER_MEDIA_PUBLISH to publish it.",
)
def INSTAGRAM_POST_IG_USER_MEDIA(
    image_url: Annotated[Optional[str], "Image URL for photo post"] = None,
    video_url: Annotated[Optional[str], "Video URL for video/reel post"] = None,
    caption: Annotated[Optional[str], "Caption for the media"] = None,
    media_type: Annotated[Optional[str], "Media type (IMAGE or VIDEO)"] = None,
    cover_url: Annotated[Optional[str], "Cover image URL for video/reel"] = None,
    is_carousel_item: Annotated[Optional[bool], "Set True if this media is part of a carousel"] = None,
    children: Annotated[Optional[List[str]], "List of child media container IDs for carousel"] = None,
    location_id: Annotated[Optional[str], "Location ID to tag in the post"] = None,
    user_tags: Annotated[Optional[List[Dict[str, Any]]], "List of user tags (JSON format)"] = None,
    thumb_offset: Annotated[Optional[int], "Thumbnail offset for video (in seconds)"] = None,
    share_to_feed: Annotated[Optional[bool], "Share to feed (for Reels)"] = None,
    audio_name: Annotated[Optional[str], "Audio name for Reels"] = None,
    collaborators: Annotated[Optional[List[str]], "List of collaborator user IDs"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Create a media container for Instagram posts."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        # Validate that either image_url or video_url is provided
        if not image_url and not video_url and not children:
            raise ValueError("Either image_url, video_url, or children must be provided")
        
        # Determine media type if not provided
        if not media_type:
            if video_url:
                media_type = "VIDEO"
            elif image_url:
                media_type = "IMAGE"
            elif children:
                media_type = "CAROUSEL"
        else:
            media_type = media_type.upper()
        
        # Build params
        params = {
            "media_type": media_type,
        }
        
        if image_url:
            params["image_url"] = image_url
        if video_url:
            params["video_url"] = video_url
        if caption:
            params["caption"] = caption
        if cover_url:
            params["cover_url"] = cover_url
        if is_carousel_item is True:
            params["is_carousel_item"] = True
        if children:
            params["children"] = ",".join(children) if isinstance(children, list) else children
        if location_id:
            params["location_id"] = location_id
        if user_tags:
            params["user_tags"] = json.dumps(user_tags) if isinstance(user_tags, list) else user_tags
        if thumb_offset is not None:
            params["thumb_offset"] = thumb_offset
        if share_to_feed is not None:
            params["share_to_feed"] = share_to_feed
        if audio_name:
            params["audio_name"] = audio_name
        if collaborators:
            params["collaborators"] = ",".join(collaborators) if isinstance(collaborators, list) else collaborators
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", f"{ig_user_id}/media", data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", f"{ig_user_id}/media", data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to create media container: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "CREATE_CAROUSEL_CONTAINER",
    description="Create Carousel Container. Create a draft carousel post with multiple images/videos before publishing. PARAMETER: children - Array of container IDs. First create individual media containers using CREATE_MEDIA_CONTAINER with is_carousel_item=True, then use their 'id' values in this children array. Returns a 'id' field (creation_id) that you must use in CREATE_POST, POST_IG_USER_MEDIA_PUBLISH, or GET_POST_STATUS to publish.",
)
def INSTAGRAM_CREATE_CAROUSEL_CONTAINER(
    children: Annotated[Optional[List[str]], "List of child media container IDs (optional)"] = None,
    child_image_files: Annotated[Optional[List[str]], "List of local image file paths (not supported yet)"] = None,
    child_image_urls: Annotated[Optional[List[str]], "List of image URLs to create child containers"] = None,
    child_video_files: Annotated[Optional[List[str]], "List of local video file paths (not supported yet)"] = None,
    child_video_urls: Annotated[Optional[List[str]], "List of video URLs to create child containers"] = None,
    caption: Annotated[Optional[str], "Caption for the carousel post"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Create a draft carousel post with multiple images/videos before publishing."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)

        if child_image_files or child_video_files:
            raise ValueError("Local file uploads are not supported. Use child_image_urls or child_video_urls.")

        if children and (child_image_urls or child_video_urls):
            raise ValueError("Provide either children OR child_image_urls/child_video_urls, not both.")

        if not children:
            child_image_urls = child_image_urls or []
            child_video_urls = child_video_urls or []
            if not child_image_urls and not child_video_urls:
                raise ValueError("Provide children or at least one child_image_urls/child_video_urls.")

        def _create_child_container(url: str, media_type: str) -> str:
            params = {
                "media_type": media_type,
                "is_carousel_item": True,
            }
            if media_type == "IMAGE":
                params["image_url"] = url
            else:
                params["video_url"] = url
            result = make_api_request("POST", f"{ig_user_id}/media", data=params)
            creation_id = result.get("id")
            if not creation_id:
                raise ValueError("Failed to create child media container.")
            return creation_id

        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
        else:
            original_version = None

        try:
            if not children:
                children = []
                for url in child_image_urls:
                    children.append(_create_child_container(url, "IMAGE"))
                for url in child_video_urls:
                    children.append(_create_child_container(url, "VIDEO"))

            params = {
                "media_type": "CAROUSEL",
                "children": ",".join(children),
            }

            if caption:
                params["caption"] = caption

            result = make_api_request("POST", f"{ig_user_id}/media", data=params)
        finally:
            if graph_api_version:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to create carousel container: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_POST_STATUS",
    description="Get Post Status. Check the processing status of a draft post container. PARAMETER: creation_id (required) - Get from CREATE_MEDIA_CONTAINER response → 'id' field. RETURNS: 'status_code' with values: 'IN_PROGRESS' (still processing, wait and check again), 'FINISHED' (ready to publish - call CREATE_POST or POST_IG_USER_MEDIA_PUBLISH), 'ERROR' (processing failed, check error_message). WORKFLOW: Call repeatedly until status is 'FINISHED', then publish.",
)
def INSTAGRAM_GET_POST_STATUS(
    creation_id: Annotated[str, "Creation ID from media container (required)"],
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Check the processing status of a draft post container."""
    try:
        _validate_required({"creation_id": creation_id}, ["creation_id"])
        
        params = {
            "fields": "status_code"
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", creation_id, params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", creation_id, params=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except requests.exceptions.Timeout as e:
        return {
            "data": {},
            "error": f"Request timed out while checking post status. The API may be slow. Try again in a few moments. Error: {str(e)}",
            "successful": False
        }
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            error_msg = f"Request timed out. The API may be slow. Try again in a few moments. {error_msg}"
        return {
            "data": {},
            "error": f"Failed to get post status: {error_msg}",
            "successful": False
        }

@mcp.tool(
    "CREATE_POST",
    description="Create Post. Publish a draft media container to Instagram (final publishing step). PARAMETER: creation_id (required) - Get from CREATE_MEDIA_CONTAINER response → 'id' field. RETURNS: 'id' (ig_media_id of published post) - USE THIS IN: GET_IG_MEDIA_INSIGHTS (for metrics), GET_IG_MEDIA_COMMENTS (for comments), POST_IG_COMMENT_REPLIES (to reply to comments). Auto-retries up to ~45s if media still processing (error 9007). For large videos, use GET_POST_STATUS first to confirm 'FINISHED' status. WORKFLOW: CREATE_MEDIA_CONTAINER → GET_POST_STATUS → CREATE_POST.",
)
def INSTAGRAM_CREATE_POST(
    creation_id: Annotated[str, "Creation_id from media container (required)"],
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Publish a draft media container to Instagram (final publishing step)."""
    try:
        _validate_required({"creation_id": creation_id}, ["creation_id"])
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        # Check status first and wait if needed
        max_retries = 15
        retry_delay = 3
        
        for attempt in range(max_retries):
            # Avoid calling the tool wrapper directly; query status via API.
            status_params = {"fields": "status_code"}
            if graph_api_version:
                original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
                try:
                    status_data = make_api_request("GET", creation_id, params=status_params)
                finally:
                    if original_version:
                        os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                    elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                        del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
            else:
                status_data = make_api_request("GET", creation_id, params=status_params)

            status_code = status_data.get("status_code")
            if status_code == "FINISHED":
                break
            if status_code == "ERROR":
                return {
                    "data": {},
                    "error": "Media container processing failed",
                    "successful": False
                }

            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 10)  # Exponential backoff, max 10s
        
        # Publish the media
        params = {
            "creation_id": creation_id,
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", f"{ig_user_id}/media_publish", data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", f"{ig_user_id}/media_publish", data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to create post: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "POST_IG_USER_MEDIA_PUBLISH",
    description="Publish IG User Media. Publish a media container to Instagram with automatic polling. PARAMETER: creation_id (required) - Get from CREATE_MEDIA_CONTAINER response → 'id' field. max_wait_seconds (optional, default 45) - How long to wait for processing. RETURNS: 'id' (ig_media_id of published post) - USE THIS IN: GET_IG_MEDIA_INSIGHTS, GET_IG_MEDIA_COMMENTS, POST_IG_COMMENT_REPLIES. Auto-polls status until FINISHED, then publishes. Rate limit: 25 posts per 24 hours. For videos >45s processing time, manually use GET_POST_STATUS first.",
)
def INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
    creation_id: Annotated[str, "Creation ID from media container (required)"],
    max_wait_seconds: Annotated[Optional[int], "Maximum time to wait for processing (seconds)"] = 45,
    poll_interval_seconds: Annotated[Optional[int], "Interval between status checks (seconds)"] = 3,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Publish a media container to an Instagram Business account with automatic polling."""
    try:
        _validate_required({"creation_id": creation_id}, ["creation_id"])
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        # Limit max_wait to stay under typical MCP client timeout (60s)
        # Reserve some time for the actual publish call
        max_wait = min(max_wait_seconds or 45, 45)  # Cap at 45 seconds
        poll_interval = poll_interval_seconds or 3
        max_retries = max_wait // poll_interval if poll_interval > 0 else 15
        
        # Poll for FINISHED status
        start_time = time.time()
        for attempt in range(max_retries):
            # Check if we've exceeded max wait time
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                return {
                    "data": {},
                    "error": f"Media container did not finish processing within {max_wait} seconds. Status may still be IN_PROGRESS. Try again later or check status manually.",
                    "successful": False
                }
            
            # Check status
            status_params = {"fields": "status_code"}
            if graph_api_version:
                original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
                try:
                    status_data = make_api_request("GET", creation_id, params=status_params)
                finally:
                    if original_version:
                        os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                    elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                        del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
            else:
                status_data = make_api_request("GET", creation_id, params=status_params)
            
            status_code = status_data.get("status_code")
            if status_code == "FINISHED":
                break
            if status_code == "ERROR":
                return {
                    "data": {},
                    "error": "Media container processing failed with ERROR status",
                    "successful": False
                }
            
            # Wait before next poll (except on last attempt)
            if attempt < max_retries - 1:
                time.sleep(poll_interval)
        
        # Final status check
        status_params = {"fields": "status_code"}
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                final_status = make_api_request("GET", creation_id, params=status_params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            final_status = make_api_request("GET", creation_id, params=status_params)
        
        if final_status.get("status_code") != "FINISHED":
            return {
                "data": {},
                "error": f"Media container status is '{final_status.get('status_code')}', not FINISHED. Processing may still be in progress.",
                "successful": False
            }
        
        # Publish the media
        params = {
            "creation_id": creation_id,
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", f"{ig_user_id}/media_publish", data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", f"{ig_user_id}/media_publish", data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except requests.exceptions.Timeout as e:
        return {
            "data": {},
            "error": f"Request timed out during media publishing. The polling may have taken too long. Try using GET_POST_STATUS to check status manually, then publish when ready. Error: {str(e)}",
            "successful": False
        }
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            error_msg = f"Request timed out. The polling may have taken too long. Try reducing max_wait_seconds or use GET_POST_STATUS to check status manually. {error_msg}"
        return {
            "data": {},
            "error": f"Failed to publish media: {error_msg}",
            "successful": False
        }

@mcp.tool(
    "GET_USER_INFO",
    description="Get User Info. Get Instagram user info including profile details and statistics. RETURNS: User profile with 'id' (instagram_user_id - auto-detected so rarely needed), username, biography, profile_picture_url, followers_count, follows_count, media_count. The ig_user_id parameter is auto-detected from your access token - you typically don't need to provide it.",
)
def INSTAGRAM_GET_USER_INFO(
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Get Instagram user info including profile details and statistics."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {
            "fields": "id,username,website,biography,profile_picture_url,followers_count,follows_count,media_count"
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", ig_user_id, params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", ig_user_id, params=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful guidance for field errors
        if "nonexisting field" in error_msg.lower() or "#100" in error_msg:
            error_msg += " Note: Some fields may not be available for all account types or may require specific permissions."
        
        return {
            "data": {},
            "error": f"Failed to get user info: {error_msg}",
            "successful": False
        }

@mcp.tool(
    "GET_USER_INSIGHTS",
    description="Get User Insights. Get Instagram account-level insights and analytics (profile views, reach, follower count, etc.). IMPORTANT: You cannot mix metrics with different metric_type requirements in one request. Metrics requiring total_value (profile_views, reach) must use metric_type='total_value'. Metrics like follower_count don't support total_value - omit metric_type or use time_series for those. Valid metrics: reach, follower_count, website_clicks, profile_views, online_followers, accounts_engaged, total_interactions, views, etc. Note: 'impressions' is NOT valid for user insights (only for media insights). breakdown: Only applicable when metric_type=total_value and only for supported metrics. timeframe: Required for demographics-related metrics and overrides since/until for those metrics.",
)
def INSTAGRAM_GET_USER_INSIGHTS(
    metric: Annotated[List[str], "Metrics to retrieve (required)"],
    period: Annotated[Optional[str], "Aggregation period"] = "day",
    metric_type: Annotated[Optional[str], "Metric type: time_series or total_value (optional)"] = None,
    breakdown: Annotated[Optional[str], "Breakdown (only applicable when metric_type=total_value)"] = None,
    since: Annotated[Optional[str], "Start date (ISO 8601 format)"] = None,
    until: Annotated[Optional[str], "End date (ISO 8601 format)"] = None,
    timeframe: Annotated[Optional[str], "Timeframe (required for demographics-related metrics)"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Get Instagram account-level insights and analytics."""
    try:
        _validate_required({"metric": metric}, ["metric"])
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {
            "metric": ",".join(metric),
            "period": period or "day"
        }
        
        if metric_type:
            params["metric_type"] = metric_type
        if breakdown:
            params["breakdown"] = breakdown
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if timeframe:
            params["timeframe"] = timeframe
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_user_id}/insights", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_user_id}/insights", params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful guidance for common errors
        if "must be one of the following values" in error_msg.lower():
            error_msg += " Valid metrics for user insights: reach, follower_count, website_clicks, profile_views, online_followers, accounts_engaged, total_interactions, likes, comments, shares, saves, replies, views, profile_links_taps, follows_and_unfollows, and demographics metrics. Note: 'impressions' is NOT valid for user insights (only for media insights)."
        elif "should be specified with parameter metric_type" in error_msg.lower():
            if "total_value" in error_msg.lower():
                error_msg += " Solution: Some metrics (like 'profile_views', 'reach') REQUIRE metric_type='total_value', while others (like 'follower_count') don't support it. You cannot mix these in one request. Make separate requests: 1) For metrics requiring total_value: use metric_type='total_value' with ['profile_views', 'reach'], 2) For follower_count: omit metric_type or use metric_type='time_series'."
        elif "incompatible with the metric type" in error_msg.lower() or "incompatible" in error_msg.lower():
            if "total_value" in error_msg.lower():
                error_msg += " Solution: Some metrics like 'follower_count' don't support metric_type='total_value'. Try removing metric_type or use metric_type='time_series', or use different metrics that support total_value (e.g., 'profile_views', 'reach')."
            elif "time_series" in error_msg.lower():
                error_msg += " Solution: Some metrics don't support time_series. Try using metric_type='total_value' or remove metric_type parameter."
        elif "permission" in error_msg.lower() or "#10" in error_msg:
            error_msg += " To fix: Generate a new token with 'instagram_manage_insights' permission from Graph API Explorer."
        
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get user insights: {error_msg}",
            "successful": False
        }

@mcp.tool(
    "GET_USER_MEDIA",
    description="Get User Media. Get Instagram user's media (posts, photos, videos). RETURNS: Array of media objects, each containing 'id' (ig_media_id) that you can use in: GET_IG_MEDIA_INSIGHTS (for metrics), GET_IG_MEDIA_COMMENTS/GET_POST_COMMENTS (to get comments), POST_IG_COMMENT_REPLIES/REPLY_TO_COMMENT (to reply), DELETE_COMMENT (to delete). Also returns media_type, caption, timestamp, permalink, etc. PAGINATION: Use 'after' cursor from response for next page.",
)
def INSTAGRAM_GET_USER_MEDIA(
    limit: Annotated[Optional[int], "Number of media items to retrieve"] = 25,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Get Instagram user's media (posts, photos, videos)."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {}
        
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_user_id}/media", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_user_id}/media", params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get user media: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_USER_MEDIA",
    description="Get IG User Media. Get Instagram user's media collection (posts, photos, videos, reels, carousels). Returns media objects with 'id' field that you can use as ig_media_id in: GET_IG_MEDIA_COMMENTS, POST_IG_MEDIA_COMMENTS, GET_POST_INSIGHTS, GET_IG_MEDIA, DELETE_IG_MEDIA. Use when you need to retrieve all media published by an Instagram Business or Creator account with support for pagination and time-based filtering.",
)
def INSTAGRAM_GET_IG_USER_MEDIA(
    fields: Annotated[Optional[str], "Fields to return"] = "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username",
    limit: Annotated[Optional[int], "Number of media items to retrieve"] = 25,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    before: Annotated[Optional[str], "Paging cursor: before"] = None,
    since: Annotated[Optional[str], "Filter media created after this timestamp (ISO 8601 format)"] = None,
    until: Annotated[Optional[str], "Filter media created before this timestamp (ISO 8601 format)"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Get Instagram user's media collection with pagination and time-based filtering."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {
            "fields": fields or "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username"
        }
        
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_user_id}/media", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_user_id}/media", params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get user media: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_USER_STORIES",
    description="Get IG User Stories. Get active story media objects for an Instagram Business or Creator account. Returns stories that are currently active within the 24-hour window. Use this to retrieve story content, metadata, and engagement metrics for monitoring or analytics purposes.",
)
def INSTAGRAM_GET_IG_USER_STORIES(
    fields: Annotated[Optional[str], "Fields to return"] = "id,media_type,media_url,permalink,timestamp",
    limit: Annotated[Optional[int], "Number of stories to retrieve"] = None,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    before: Annotated[Optional[str], "Paging cursor: before"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Get active story media objects for an Instagram Business or Creator account."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {
            "fields": fields or "id,media_type,media_url,permalink,timestamp"
        }
        
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_user_id}/stories", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_user_id}/stories", params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get user stories: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_USER_TAGS",
    description="Get IG User Tags. Get Instagram media where the user has been tagged by other users. Use when you need to retrieve all media in which an Instagram Business or Creator account has been tagged, including tags in captions, comments, or on the media itself.",
)
def INSTAGRAM_GET_IG_USER_TAGS(
    fields: Annotated[Optional[str], "Fields to return"] = "id,caption,media_type,media_url,permalink,timestamp,username",
    limit: Annotated[Optional[int], "Number of tagged media items to retrieve"] = 25,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    before: Annotated[Optional[str], "Paging cursor: before"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Get Instagram media where the user has been tagged by other users."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {
            "fields": fields or "id,caption,media_type,media_url,permalink,timestamp,username"
        }
        
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_user_id}/tags", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_user_id}/tags", params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get user tags: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_USER_CONTENT_PUBLISHING_LIMIT",
    description="Get IG User Content Publishing Limit. Get an Instagram Business Account's current content publishing usage. Use this to monitor quota usage and avoid hitting rate limits when publishing content via the API.",
)
def INSTAGRAM_GET_IG_USER_CONTENT_PUBLISHING_LIMIT(
    fields: Annotated[Optional[str], "Fields to return"] = "quota_usage,config",
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Get an Instagram Business Account's current content publishing usage."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {
            "fields": fields or "quota_usage,config"
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_user_id}/content_publishing_limit", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_user_id}/content_publishing_limit", params=params)
        
        return {
            "data": result.get("data", []),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": [],
            "error": f"Failed to get content publishing limit: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_USER_LIVE_MEDIA",
    description="Get IG User Live Media. Get live media objects during an active Instagram broadcast. Returns the live video media ID and metadata when a live broadcast is in progress on an Instagram Business or Creator account. Use this to monitor active live streams and access real-time engagement data.",
)
def INSTAGRAM_GET_IG_USER_LIVE_MEDIA(
    fields: Annotated[Optional[str], "Fields to return"] = "id,media_type,media_url,timestamp,permalink",
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Get live media objects during an active Instagram broadcast."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {
            "fields": fields or "id,media_type,media_url,timestamp,permalink"
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_user_id}/live_media", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_user_id}/live_media", params=params)
        
        # Check if there's no live broadcast (empty data array)
        live_media_data = result.get("data", [])
        if not live_media_data:
            return {
                "data": result,
                "error": "",
                "successful": True,
                "message": "No active live broadcast found. The account is not currently live streaming."
            }
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to get live media: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_MEDIA_COMMENTS",
    description="Get IG Media Comments. Retrieve comments on an Instagram media object. PARAMETER: ig_media_id (required) - Get from: 1) GET_USER_MEDIA response → 'id' field, OR 2) CREATE_POST/POST_IG_USER_MEDIA_PUBLISH response → 'id' field. RETURNS: Array of comment objects containing: 'id' (comment_id) - use in POST_IG_COMMENT_REPLIES, REPLY_TO_COMMENT, DELETE_COMMENT; 'text' - comment content; 'username' - commenter; 'timestamp'. PAGINATION: Use 'after' cursor for more comments.",
)
def INSTAGRAM_GET_IG_MEDIA_COMMENTS(
    ig_media_id: Annotated[str, "Instagram media ID (required)"],
    fields: Annotated[Optional[str], "Fields to return"] = None,
    limit: Annotated[Optional[int], "Max comments to return"] = 25,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    before: Annotated[Optional[str], "Paging cursor: before"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Retrieve comments on an Instagram media object."""
    try:
        _validate_required({"ig_media_id": ig_media_id}, ["ig_media_id"])
        
        params = {
            "fields": fields or "id,text,username,timestamp,like_count,from,hidden,media,parent_id"
        }
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_media_id}/comments", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_media_id}/comments", params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get media comments: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_POST_COMMENTS",
    description="Get Post Comments. Get comments on an Instagram post. PARAMETER: ig_post_id (required) - Get from: 1) GET_USER_MEDIA response → 'id' field, OR 2) CREATE_POST/POST_IG_USER_MEDIA_PUBLISH response → 'id' field. RETURNS: Array of comment objects containing: 'id' (comment_id) - use in POST_IG_COMMENT_REPLIES, REPLY_TO_COMMENT, DELETE_COMMENT; 'text'; 'username'; 'timestamp'. Same as GET_IG_MEDIA_COMMENTS but with different field naming.",
)
def INSTAGRAM_GET_POST_COMMENTS(
    ig_post_id: Annotated[str, "Instagram post ID (required)"],
    limit: Annotated[Optional[int], "Number of comments to retrieve"] = 25,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Get comments on an Instagram post."""
    try:
        _validate_required({"ig_post_id": ig_post_id}, ["ig_post_id"])
        
        params = {}
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_post_id}/comments", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_post_id}/comments", params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get post comments: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_POST_INSIGHTS",
    description="Get Post Insights. Get Instagram post insights/analytics (impressions, reach, engagement, etc.). PARAMETER: ig_media_id - Get this from GET_USER_MEDIA response (the 'id' field of a media object).",
)
def INSTAGRAM_GET_POST_INSIGHTS(
    ig_post_id: Annotated[str, "Instagram post ID (required)"],
    metric_preset: Annotated[Optional[str], "Metric preset to use"] = "auto_safe",
    metric: Annotated[Optional[List[str]], "Specific metrics to retrieve (optional, overrides metric_preset if provided)"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Get Instagram post insights/analytics."""
    try:
        _validate_required({"ig_post_id": ig_post_id}, ["ig_post_id"])
        
        params = {}
        
        # Use metric_preset if no specific metrics provided
        if metric:
            params["metric"] = ",".join(metric)
        else:
            params["metric_preset"] = metric_preset or "auto_safe"
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_post_id}/insights", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_post_id}/insights", params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful guidance for common errors
        if "impressions" in error_msg.lower() and "no longer supported" in error_msg.lower():
            error_msg += " Solution: Remove 'impressions' from your metrics list. Use 'reach' instead, or specify graph_api_version='v21.0' to use an older API version that supports impressions."
        elif "permission" in error_msg.lower() or "#10" in error_msg:
            error_msg += " To fix: Generate a new token with 'instagram_manage_insights' permission from Graph API Explorer."
        
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get post insights: {error_msg}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_MEDIA",
    description="Get Instagram Media. Get a published Instagram Media object (photo, video, story, reel, or carousel). PARAMETER: ig_media_id - Get this from GET_USER_MEDIA response (the 'id' field of a media object) or from CREATE_POST/POST_IG_USER_MEDIA_PUBLISH response (the 'id' field after publishing). Use when you need to retrieve detailed information about a specific Instagram post including engagement metrics, caption, media URLs, and metadata. NOTE: This action is for published media only. For unpublished container IDs (from CREATE_MEDIA_CONTAINER), use GET_POST_STATUS to check status instead.",
)
def INSTAGRAM_GET_IG_MEDIA(
    ig_media_id: Annotated[str, "Instagram media ID (required)"],
    fields: Annotated[Optional[str], "Fields to return"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Get a published Instagram media object."""
    try:
        _validate_required({"ig_media_id": ig_media_id}, ["ig_media_id"])

        params = {
            "fields": fields or "id"
        }

        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", ig_media_id, params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", ig_media_id, params=params)

        return {
            "data": result,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to get IG media: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_MEDIA_CHILDREN",
    description="Get IG Media Children. Tool to get media objects (images/videos) that are children of an Instagram carousel/album post. PARAMETER: ig_media_id - Get this from GET_USER_MEDIA response (the 'id' field of a carousel media object). Use when you need to retrieve individual media items from a carousel album post. Note: Carousel children media do not support insights queries - for analytics, query metrics at the parent carousel level.",
)
def INSTAGRAM_GET_IG_MEDIA_CHILDREN(
    ig_media_id: Annotated[str, "Instagram media ID (required)"],
    fields: Annotated[Optional[str], "Fields to return"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Get children of a carousel/album post."""
    try:
        _validate_required({"ig_media_id": ig_media_id}, ["ig_media_id"])

        params = {
            "fields": fields or "id,media_type,media_url,permalink,timestamp"
        }

        endpoint = f"{ig_media_id}/children"

        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", endpoint, params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", endpoint, params=params)

        return {
            "data": result.get("data", []),
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": [],
            "error": f"Failed to get media children: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "POST_IG_MEDIA_COMMENTS",
    description="Post IG Media Comments. Tool to create a comment on an Instagram media object. PARAMETER: ig_media_id - Get this from GET_USER_MEDIA response (the 'id' field of a media object). Use when you need to post a comment on a specific Instagram post, photo, video, or carousel. The comment must be 300 characters or less, contain at most 4 hashtags and 1 URL, and cannot consist entirely of capital letters.",
)
def INSTAGRAM_POST_IG_MEDIA_COMMENTS(
    ig_media_id: Annotated[str, "Instagram media ID (required)"],
    message: Annotated[str, "Comment message (required, max 300 chars, max 4 hashtags, max 1 URL)"],
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Create a comment on an Instagram media object."""
    try:
        _validate_required({"ig_media_id": ig_media_id, "message": message}, ["ig_media_id", "message"])
        
        params = {
            "message": message
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", f"{ig_media_id}/comments", data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", f"{ig_media_id}/comments", data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to post media comment: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "POST_IG_COMMENT_REPLIES",
    description="Post IG Comment Replies. Reply to an Instagram comment. PARAMETERS: ig_comment_id (required) - Get from GET_IG_MEDIA_COMMENTS or GET_POST_COMMENTS response → 'id' field of the comment to reply to. message (required) - Your reply text. CONSTRAINTS: Max 300 chars, max 4 hashtags, max 1 URL, cannot be all caps. RETURNS: 'id' of the new reply comment. WORKFLOW: GET_USER_MEDIA → GET_IG_MEDIA_COMMENTS → POST_IG_COMMENT_REPLIES with comment's 'id'.",
)
def INSTAGRAM_POST_IG_COMMENT_REPLIES(
    ig_comment_id: Annotated[str, "Instagram comment ID to reply to (required)"],
    message: Annotated[str, "Reply message (required, max 300 chars, max 4 hashtags, max 1 URL)"],
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Create a reply to an Instagram comment."""
    try:
        _validate_required({"ig_comment_id": ig_comment_id, "message": message}, ["ig_comment_id", "message"])
        
        params = {
            "message": message
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", f"{ig_comment_id}/replies", data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", f"{ig_comment_id}/replies", data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to post comment reply: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "POST_IG_USER_MENTIONS",
    description="Reply to IG User Mentions. Tool to reply to a mention of your Instagram Business or Creator account. Use when you need to respond to comments or media captions where your account has been @mentioned by another Instagram user. This creates a comment on the media or comment containing the mention.",
)
def INSTAGRAM_POST_IG_USER_MENTIONS(
    media_id: Annotated[str, "Media ID where the mention is located (required)"],
    message: Annotated[str, "Reply message (required, max 300 chars, max 4 hashtags, max 1 URL)"],
    comment_id: Annotated[Optional[str], "Comment ID if replying to a comment mention (optional)"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """Reply to a mention of your Instagram Business or Creator account."""
    try:
        _validate_required({"media_id": media_id, "message": message}, ["media_id", "message"])
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        params = {
            "message": message
        }
        
        # If comment_id is provided, reply to the comment. Otherwise, comment on the media.
        if comment_id:
            endpoint = f"{comment_id}/replies"
        else:
            endpoint = f"{media_id}/comments"
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", endpoint, data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", endpoint, data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to reply to mention: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "REPLY_TO_COMMENT",
    description="Reply To Comment. Reply to a comment on Instagram media. PARAMETERS: ig_comment_id (required) - Get from GET_IG_MEDIA_COMMENTS or GET_POST_COMMENTS response → 'id' field of the comment to reply to. message (required) - Your reply text. RETURNS: 'id' of the new reply. Similar to POST_IG_COMMENT_REPLIES. WORKFLOW: GET_USER_MEDIA → GET_IG_MEDIA_COMMENTS/GET_POST_COMMENTS → REPLY_TO_COMMENT with comment's 'id'.",
)
def INSTAGRAM_REPLY_TO_COMMENT(
    ig_comment_id: Annotated[str, "Instagram comment ID to reply to (required)"],
    message: Annotated[str, "Reply message (required)"],
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Reply to a comment on Instagram media."""
    try:
        _validate_required({"ig_comment_id": ig_comment_id, "message": message}, ["ig_comment_id", "message"])
        
        params = {
            "message": message
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", f"{ig_comment_id}/replies", data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", f"{ig_comment_id}/replies", data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to reply to comment: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_COMMENT_REPLIES",
    description="Get IG Comment Replies. Get replies to a specific Instagram comment. PARAMETERS: ig_media_id - Get from GET_USER_MEDIA response (the 'id' field). comment_id - Get from GET_IG_MEDIA_COMMENTS or GET_POST_COMMENTS response (the 'id' field of a comment object). Returns a list of comment replies with details like text, username, timestamp, and like count. Use when you need to retrieve child comments (replies) for a specific parent comment.",
)
def INSTAGRAM_GET_IG_COMMENT_REPLIES(
    ig_comment_id: Annotated[str, "Instagram comment ID (required)"],
    fields: Annotated[Optional[str], "Fields to return"] = None,
    limit: Annotated[Optional[int], "Max replies to return"] = 25,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    before: Annotated[Optional[str], "Paging cursor: before"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Get replies to a specific Instagram comment."""
    try:
        _validate_required({"ig_comment_id": ig_comment_id}, ["ig_comment_id"])

        params = {
            "fields": fields or "id,text,username,timestamp,like_count,hidden,from,media,parent_id,legacy_instagram_comment_id",
        }
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        endpoint = f"{ig_comment_id}/replies"

        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", endpoint, params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", endpoint, params=params)

        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get comment replies: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "DELETE_COMMENT",
    description="Delete Comment. Delete a comment on Instagram media. PARAMETER: ig_comment_id (required) - Get from GET_IG_MEDIA_COMMENTS or GET_POST_COMMENTS response → 'id' field of the comment to delete. RETURNS: Success boolean. PERMISSIONS: Can delete your own comments anywhere, or any comment on your own posts. Cannot delete other users' comments on others' posts. WORKFLOW: GET_USER_MEDIA → GET_IG_MEDIA_COMMENTS → DELETE_COMMENT with comment's 'id'.",
)
def INSTAGRAM_DELETE_COMMENT(
    ig_comment_id: Annotated[str, "Instagram comment ID to delete (required)"],
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Delete a comment on Instagram media."""
    try:
        _validate_required({"ig_comment_id": ig_comment_id}, ["ig_comment_id"])
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("DELETE", ig_comment_id)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("DELETE", ig_comment_id)
        
        return {
            "data": result if result else {"success": True},
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to delete comment: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_IG_MEDIA_INSIGHTS",
    description="Get IG Media Insights. Get metrics for Instagram media. PARAMETERS: ig_media_id (required) - Get from: 1) GET_USER_MEDIA response → 'id' field, OR 2) CREATE_POST/POST_IG_USER_MEDIA_PUBLISH response → 'id' field (MUST be published media, NOT container ID). metric (required) - Array of metrics like ['reach', 'likes', 'comments', 'shares', 'saved']. IMPORTANT: Only works on PUBLISHED posts, not container IDs. API v22.0+: 'impressions' not supported, use 'reach'. Requirements: Media <2 years old, account needs 1000+ followers for some metrics.",
)
def INSTAGRAM_GET_IG_MEDIA_INSIGHTS(
    ig_media_id: Annotated[str, "Instagram media ID (required)"],
    metric: Annotated[List[str], "Metrics to retrieve (required). For v22.0+: reach, likes, comments, shares, saved, video_views, plays, total_interactions, views, replies. Note: 'impressions' is NOT supported in v22.0+ - use 'reach' instead."],
    period: Annotated[Optional[str], "Aggregation period (default: lifetime)"] = "lifetime",
    graph_api_version: Annotated[Optional[str], "Graph API version (optional, defaults to INSTAGRAM_GRAPH_API_VERSION env var or v21.0)"] = None,
):
    """Get insights for an Instagram media object."""
    try:
        _validate_required({"ig_media_id": ig_media_id, "metric": metric}, ["ig_media_id", "metric"])
        
        # Get the API version being used
        api_version = graph_api_version or get_graph_api_version()
        # Check if version is v22.0 or higher
        try:
            version_num = int(api_version.replace("v", "").split(".")[0])
            is_v22_plus = version_num >= 22
        except:
            is_v22_plus = False
        
        # Auto-remove impressions if using v22.0+ and suggest reach instead
        if is_v22_plus and "impressions" in metric:
            metric = [m for m in metric if m != "impressions"]
            if "reach" not in metric:
                metric.append("reach")

        params = {
            "metric": ",".join(metric),
            "period": period or "lifetime",
        }

        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", f"{ig_media_id}/insights", params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", f"{ig_media_id}/insights", params=params)

        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful guidance for common errors
        if "impressions" in error_msg.lower() and "no longer supported" in error_msg.lower():
            error_msg += " Solution: Remove 'impressions' from your metrics list. Use 'reach' instead, or specify graph_api_version='v21.0' to use an older API version that supports impressions."
        elif "metric" in error_msg.lower() and "must be one of" in error_msg.lower():
            error_msg += " Common valid metrics for v22.0+: reach, likes, comments, shares, saved, video_views, plays, total_interactions, views, replies."
        elif "permission" in error_msg.lower() or "#10" in error_msg:
            error_msg += " To fix: Generate a new token with 'instagram_manage_insights' permission from Graph API Explorer."
        
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get IG media insights: {error_msg}",
            "successful": False
        }

@mcp.tool(
    "GET_CONVERSATION",
    description="Get Conversation. Get details about a specific Instagram DM conversation (participants, etc). PARAMETER: conversation_id - Get this from LIST_ALL_CONVERSATIONS response (the 'id' field of a conversation object). RETURNS: Conversation details including 'id', 'participants' array (each with 'id' you can use as recipient_id in SEND_TEXT_MESSAGE, SEND_IMAGE), and 'updated_time'.",
)
def INSTAGRAM_GET_CONVERSATION(
    conversation_id: Annotated[str, "Conversation ID (required)"],
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Get details about a specific Instagram DM conversation."""
    try:
        _validate_required({"conversation_id": conversation_id}, ["conversation_id"])

        params = {
            "fields": "id,participants,updated_time"
        }
        endpoint = conversation_id

        ig_user_id = _get_instagram_user_id(None)
        page_info = _get_page_for_ig_account(ig_user_id)
        page_access_token = page_info.get("page_access_token")
        
        if not page_info.get("page_id"):
            raise ValueError("Could not find Facebook Page ID. Connect your Instagram account to a Facebook Page or set FACEBOOK_PAGE_ID environment variable.")
        
        if not page_access_token:
            raise ValueError(
                "Page Access Token is required for conversations API. "
                "Run: uv run instagram-mcp/get_page_token.py to get it automatically, "
                "or set INSTAGRAM_PAGE_ACCESS_TOKEN environment variable."
            )
        
        # Store original tokens to restore later
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        original_oauth_token = os.environ.get("INSTAGRAM_OAUTH_ACCESS_TOKEN")
        original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
        
        try:
            # Set graph API version if provided
            if graph_api_version:
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            
            # CRITICAL: Set page access token to INSTAGRAM_ACCESS_TOKEN so get_access_token() uses it
            os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_access_token
            os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = page_access_token
            
            # Make the API request
            result = make_api_request("GET", endpoint, params=params)
            
        finally:
            # Restore original tokens
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
            
            if original_oauth_token:
                os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = original_oauth_token
            elif "INSTAGRAM_OAUTH_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"]
            
            # Restore graph API version
            if original_version:
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
            elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ and not graph_api_version:
                del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to get conversation: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "GET_CONVERSATIONS",
    description="Get Conversations. List Instagram DM conversations to find conversation IDs. Returns conversation objects with 'id' field that you can use as conversation_id in: GET_CONVERSATION, LIST_ALL_MESSAGES. Also returns 'participants' array with user IDs that you can use as recipient_id in: SEND_TEXT_MESSAGE, SEND_IMAGE, MARK_SEEN.",
)
def INSTAGRAM_GET_CONVERSATIONS(
    page_id: Annotated[Optional[str], "Facebook Page ID (optional, auto-detected if not provided)"] = None,
    limit: Annotated[Optional[int], "Number of conversations to retrieve (optional)"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """List Instagram DM conversations to find conversation IDs."""
    try:
        ig_user_id = _get_instagram_user_id(None)
        page_info = _get_page_for_ig_account(ig_user_id)

        if page_id:
            page_info["page_id"] = page_id

        page_id_value = page_info.get("page_id")
        page_access_token = page_info.get("page_access_token")
        
        if not page_id_value:
            raise ValueError("Could not find Facebook Page ID. Connect your Instagram account to a Facebook Page or set FACEBOOK_PAGE_ID environment variable.")
        
        if not page_access_token:
            raise ValueError(
                "Page Access Token is required for conversations API. "
                "Run: uv run instagram-mcp/get_page_token.py to get it automatically, "
                "or set INSTAGRAM_PAGE_ACCESS_TOKEN environment variable."
            )

        params = {
            "platform": "instagram",
            "fields": "id,participants,updated_time"
        }
        if limit:
            params["limit"] = limit

        endpoint = f"{page_id_value}/conversations"

        # Instagram Conversations API requires Page Access Token
        # Store original tokens to restore later
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        original_oauth_token = os.environ.get("INSTAGRAM_OAUTH_ACCESS_TOKEN")
        original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
        
        try:
            # Set graph API version if provided
            if graph_api_version:
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            
            # CRITICAL: Set page access token to INSTAGRAM_ACCESS_TOKEN so get_access_token() uses it
            os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_access_token
            os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = page_access_token
            
            # Make the API request
            result = make_api_request("GET", endpoint, params=params)
            
        finally:
            # Restore original tokens
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
            
            if original_oauth_token:
                os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = original_oauth_token
            elif "INSTAGRAM_OAUTH_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"]
            
            # Restore graph API version
            if original_version:
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
            elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ and not graph_api_version:
                del os.environ["INSTAGRAM_GRAPH_API_VERSION"]

        return {
            "data": result,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to get conversations: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "LIST_ALL_CONVERSATIONS",
    description="List All Conversations. List all Instagram DM conversations for the authenticated user. NO REQUIRED PARAMETERS - everything is auto-detected. RETURNS: Array of conversation objects containing: 'id' (conversation_id) - use in GET_CONVERSATION, LIST_ALL_MESSAGES; 'participants' array with user objects containing 'id' (recipient_id) - use in SEND_TEXT_MESSAGE, SEND_IMAGE, MARK_SEEN; 'updated_time' - last activity timestamp. PAGINATION: Use 'after' cursor from response for more conversations.",
)
def INSTAGRAM_LIST_ALL_CONVERSATIONS(
    limit: Annotated[Optional[int], "Number of conversations to retrieve"] = 25,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
    ig_user_id: Annotated[Optional[str], "Instagram user ID (optional, auto-detected from access token)"] = None,
):
    """List all Instagram DM conversations for the authenticated user."""
    try:
        ig_user_id = _get_instagram_user_id(ig_user_id)
        
        page_info = _get_page_for_ig_account(ig_user_id)
        page_id = page_info.get("page_id")
        page_access_token = page_info.get("page_access_token")
        
        if not page_id:
            raise ValueError("Could not find Facebook Page ID. Connect your Instagram account to a Facebook Page or set FACEBOOK_PAGE_ID environment variable.")
        
        if not page_access_token:
            raise ValueError(
                "Page Access Token is required for conversations API. "
                "Run: uv run instagram-mcp/get_page_token.py to get it automatically, "
                "or set INSTAGRAM_PAGE_ACCESS_TOKEN environment variable."
            )
        
        params = {
            "platform": "instagram",
            "fields": "id,participants,updated_time"
        }
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        
        endpoint = f"{page_id}/conversations"
        
        # Instagram Conversations API requires Page Access Token
        # Store original tokens to restore later
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        original_oauth_token = os.environ.get("INSTAGRAM_OAUTH_ACCESS_TOKEN")
        original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
        
        try:
            # Set graph API version if provided
            if graph_api_version:
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            
            # Use page access token (we already verified it exists above)
            # Instagram Conversations API requires a Page Access Token, not a User Access Token
            if page_access_token:
                # We have a page access token - use it
                # CRITICAL: Set it in INSTAGRAM_ACCESS_TOKEN so get_access_token() uses it
                # get_access_token() checks INSTAGRAM_ACCESS_TOKEN first
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_access_token
                # Also set in OAuth location as backup
                os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = page_access_token
                print(f"Using Page Access Token for conversations API (Page ID: {page_id})")
            else:
                # This should never happen since we check above, but just in case
                raise ValueError(
                    "Page Access Token is required for conversations API. "
                    "The auto-detection failed to find a page access token. "
                    "To fix: 1) Ensure your Instagram account is connected to a Facebook Page, "
                    "2) Make sure your access token has 'pages_messaging' permission, "
                    "3) Or set INSTAGRAM_PAGE_ACCESS_TOKEN environment variable directly, "
                    "4) Or run: uv run instagram-mcp/get_page_token.py"
                )
            
            # Make the API request
            # get_access_token() will now return the page_access_token we just set
            result = make_api_request("GET", endpoint, params=params)
            
        finally:
            # Restore original tokens
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ and not page_info.get("page_access_token"):
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
            
            if original_oauth_token:
                os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = original_oauth_token
            elif "INSTAGRAM_OAUTH_ACCESS_TOKEN" in os.environ and not page_info.get("page_access_token"):
                del os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"]
            
            # Restore graph API version
            if original_version:
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
            elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ and not graph_api_version:
                del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        
        # Check if result has data
        conversations_data = result.get("data", [])
        
        # If no conversations, provide helpful message
        if not conversations_data:
            return {
                "data": [],
                "paging": result.get("paging", {}),
                "error": "No conversations found. This could mean: 1) You have no active DM conversations, 2) The conversations API requires 'pages_messaging' permission, 3) You need to use a Page Access Token (not User Access Token). Ensure your access token has the correct permissions.",
                "successful": True  # Still successful, just no data
            }
        
        return {
            "data": conversations_data,
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide more specific error messages
        if "permission" in error_msg.lower() or "access" in error_msg.lower():
            error_msg += " Ensure your access token has 'pages_messaging' permission and you're using a Page Access Token."
        elif "page" in error_msg.lower():
            error_msg += " Make sure your Instagram account is connected to a Facebook Page and you have a valid Page Access Token."
        
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to list conversations: {error_msg}",
            "successful": False
        }

@mcp.tool(
    "LIST_ALL_MESSAGES",
    description="List All Messages. List all messages from a specific Instagram DM conversation. PARAMETER: conversation_id - Get from LIST_ALL_CONVERSATIONS response (the 'id' field). RETURNS: Array of message objects containing: 'id' (message_id) - use as reply_to_message_id in SEND_TEXT_MESSAGE or SEND_IMAGE to reply; 'message' - text content; 'from' - sender info with 'id' and 'username'; 'created_time' - timestamp; 'attachments' - any media attached. PAGINATION: Use 'after' cursor for more messages.",
)
def INSTAGRAM_LIST_ALL_MESSAGES(
    conversation_id: Annotated[str, "Conversation ID (required)"],
    limit: Annotated[Optional[int], "Number of messages to retrieve"] = 25,
    after: Annotated[Optional[str], "Paging cursor: after"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """List all messages from a specific Instagram DM conversation."""
    try:
        _validate_required({"conversation_id": conversation_id}, ["conversation_id"])
        
        params = {
            "fields": "id,message,from,created_time,attachments"
        }
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        
        ig_user_id = _get_instagram_user_id(None)
        page_info = _get_page_for_ig_account(ig_user_id)
        if not page_info.get("page_id"):
            raise ValueError("Could not find Facebook Page ID. Connect your Instagram account to a Facebook Page.")
        
        endpoint = f"{conversation_id}/messages"
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                if page_info.get("page_access_token"):
                    original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
                    os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_info["page_access_token"]
                else:
                    original_token = None
                try:
                    result = make_api_request("GET", endpoint, params=params)
                finally:
                    if original_token:
                        os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
                    elif page_info.get("page_access_token") and "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                        del os.environ["INSTAGRAM_ACCESS_TOKEN"]
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            if page_info.get("page_access_token"):
                original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_info["page_access_token"]
                try:
                    result = make_api_request("GET", endpoint, params=params)
                finally:
                    os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            else:
                result = make_api_request("GET", endpoint, params=params)
        
        return {
            "data": result.get("data", []),
            "paging": result.get("paging", {}),
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to list messages: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "SEND_TEXT_MESSAGE",
    description="Send Text Message. Send a text message to an Instagram user via DM. PARAMETERS: recipient_id (required) - Get from: 1) LIST_ALL_CONVERSATIONS response → 'participants' array → 'id' field, OR 2) GET_USER_BY_USERNAME response → 'instagram_user_id' field. text (required) - Message content. reply_to_message_id (optional) - Get from LIST_ALL_MESSAGES response → 'id' field of the message you want to reply to. RETURNS: Message 'id' and 'created_time'. NOTE: Recipient must have an open 24-hour messaging window (they messaged you first).",
)
def INSTAGRAM_SEND_TEXT_MESSAGE(
    recipient_id: Annotated[str, "Recipient Instagram user ID (required)"],
    text: Annotated[str, "Text message to send (required)"],
    ig_user_id: Annotated[Optional[str], "Instagram user ID"] = None,
    reply_to_message_id: Annotated[Optional[str], "Message ID to reply to"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Send a text message to an Instagram user via DM."""
    try:
        _validate_required({"recipient_id": recipient_id, "text": text}, ["recipient_id", "text"])
        
        if not ig_user_id:
            ig_user_id = _get_instagram_user_id(None)
        
        # Get page access token for messaging (required)
        page_info = _get_page_for_ig_account(ig_user_id)
        
        params = {
            "recipient": json.dumps({"id": recipient_id}),
            "message": json.dumps({"text": text})
        }
        
        if reply_to_message_id:
            params["message"] = json.dumps({"text": text, "reply_to": {"message_id": reply_to_message_id}})
        
        endpoint = f"{ig_user_id}/messages"
        
        # Use page access token if available (required for messaging)
        if page_info.get("page_access_token"):
            # Temporarily use page access token for this request
            original_token = os.getenv("INSTAGRAM_ACCESS_TOKEN") or os.getenv("INSTAGRAM_OAUTH_ACCESS_TOKEN")
            original_oauth_token = os.getenv("INSTAGRAM_OAUTH_ACCESS_TOKEN")
            
            # Set page access token
            if "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_info["page_access_token"]
            else:
                os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = page_info["page_access_token"]
            
            try:
                if graph_api_version:
                    original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
                    try:
                        result = make_api_request("POST", endpoint, data=params)
                    finally:
                        if original_version:
                            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                        elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                            del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
                else:
                    result = make_api_request("POST", endpoint, data=params)
            finally:
                # Restore original token
                if original_token:
                    if "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                        os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
                    if original_oauth_token:
                        os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"] = original_oauth_token
                    elif "INSTAGRAM_OAUTH_ACCESS_TOKEN" in os.environ and not original_oauth_token:
                        del os.environ["INSTAGRAM_OAUTH_ACCESS_TOKEN"]
        else:
            # No page access token available, try with regular token
            if graph_api_version:
                original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
                os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
                try:
                    result = make_api_request("POST", endpoint, data=params)
                finally:
                    if original_version:
                        os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                    elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                        del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
            else:
                result = make_api_request("POST", endpoint, data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful guidance for common errors
        if "(#3)" in error_msg or "does not have the capability" in error_msg.lower():
            error_msg += " The recipient must message you first, or your app needs App Review for Instagram Messaging."
        elif "(#100)" in error_msg or "no matching user found" in error_msg.lower():
            error_msg += "\n\nPossible causes:\n"
            error_msg += "1. The recipient hasn't messaged you first (24-hour window expired or never initiated)\n"
            error_msg += "2. The recipient_id is incorrect\n"
            error_msg += "3. The recipient must be a Business or Creator account\n"
            error_msg += "4. Use INSTAGRAM_GET_USER_BY_USERNAME to find the correct recipient_id"
        elif "permission" in error_msg.lower() or "#10" in error_msg or "#200" in error_msg:
            error_msg += "\n\nSolution: Your access token needs 'pages_messaging' and 'instagram_manage_messages' permissions. "
            error_msg += "Ensure your OAuth2 scopes include these, or generate a new token with these permissions."
        
        return {
            "data": {},
            "error": f"Failed to send text message: {error_msg}",
            "successful": False
        }

@mcp.tool(
    "GET_USER_BY_USERNAME",
    description="Get User by Username. Find an Instagram user's ID by their username using Business Discovery API. Works for Business and Creator accounts. PARAMETER: username - Just the username without @ symbol. RETURNS: 'instagram_user_id' field that you can use as recipient_id in: SEND_TEXT_MESSAGE, SEND_IMAGE, MARK_SEEN. Also returns username, name, profile_picture_url, followers_count, media_count. NOTE: Only works for public Business/Creator accounts due to API limitations.",
)
def INSTAGRAM_GET_USER_BY_USERNAME(
    username: Annotated[str, "Instagram username (without @ symbol, required)"],
    ig_user_id: Annotated[Optional[str], "Your Instagram user ID (optional, uses env var if not provided)"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Find an Instagram user's ID by their username using Business Discovery API."""
    try:
        _validate_required({"username": username}, ["username"])
        
        if not ig_user_id:
            ig_user_id = _get_instagram_user_id(None)
        
        # Remove @ if user included it
        username = username.lstrip('@')
        
        params = {
            "fields": f"business_discovery.username({username}){{id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count}}"
        }
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("GET", ig_user_id, params=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("GET", ig_user_id, params=params)
        
        # Extract the user info from business_discovery
        if "business_discovery" in result:
            user_info = result["business_discovery"]
            return {
                "data": {
                    "instagram_user_id": user_info.get("id"),
                    "username": user_info.get("username"),
                    "name": user_info.get("name"),
                    "profile_picture_url": user_info.get("profile_picture_url"),
                    "biography": user_info.get("biography"),
                    "followers_count": user_info.get("followers_count"),
                    "follows_count": user_info.get("follows_count"),
                    "media_count": user_info.get("media_count")
                },
                "error": "",
                "successful": True
            }
        else:
            return {
                "data": {},
                "error": "User not found or account is not a Business/Creator account",
                "successful": False
            }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to get user by username: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "SEND_IMAGE",
    description="Send Image. Send an image via Instagram DM to a specific user. PARAMETERS: recipient_id (required) - Get from: 1) LIST_ALL_CONVERSATIONS response → 'participants' array → 'id' field, OR 2) GET_USER_BY_USERNAME response → 'instagram_user_id' field. image_url (required) - Public URL of the image to send. RETURNS: Message 'id' and 'created_time'. NOTE: Image URL must be publicly accessible. Recipient must have an open 24-hour messaging window.",
)
def INSTAGRAM_SEND_IMAGE(
    recipient_id: Annotated[str, "Recipient Instagram user ID (required)"],
    image_url: Annotated[str, "Image URL to send (required)"],
    ig_user_id: Annotated[Optional[str], "Instagram user ID"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Send an image via Instagram DM to a specific user."""
    try:
        _validate_required({"recipient_id": recipient_id, "image_url": image_url}, ["recipient_id", "image_url"])
        
        if not ig_user_id:
            ig_user_id = _get_instagram_user_id(None)
        
        params = {
            "recipient": json.dumps({"id": recipient_id}),
            "message": json.dumps({"attachment": {"type": "image", "payload": {"url": image_url}}})
        }
        
        endpoint = f"{ig_user_id}/messages"
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", endpoint, data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", endpoint, data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to send image: {str(e)}",
            "successful": False
        }

@mcp.tool(
    "MARK_SEEN",
    description="Mark Seen. Mark Instagram DM messages as read/seen for a specific user. PARAMETER: recipient_id (required) - Get from: 1) LIST_ALL_CONVERSATIONS response → 'participants' array → 'id' field, OR 2) GET_USER_BY_USERNAME response → 'instagram_user_id' field. IMPORTANT LIMITATIONS: The sender_action API may have limited support; recipient must have active 24-hour messaging window; requires instagram_manage_messages permission; only works with Business/Creator accounts. Error 500 may indicate feature not supported for your account.",
)
def INSTAGRAM_MARK_SEEN(
    recipient_id: Annotated[str, "Recipient Instagram user ID (required)"],
    ig_user_id: Annotated[Optional[str], "Instagram user ID"] = None,
    graph_api_version: Annotated[Optional[str], "Graph API version"] = None,
):
    """Mark Instagram DM messages as read/seen for a specific user."""
    try:
        _validate_required({"recipient_id": recipient_id}, ["recipient_id"])
        
        if not ig_user_id:
            ig_user_id = _get_instagram_user_id(None)
        
        params = {
            "recipient": json.dumps({"id": recipient_id}),
            "sender_action": "mark_seen"
        }
        
        endpoint = f"{ig_user_id}/messages"
        
        if graph_api_version:
            original_version = os.environ.get("INSTAGRAM_GRAPH_API_VERSION")
            os.environ["INSTAGRAM_GRAPH_API_VERSION"] = graph_api_version
            try:
                result = make_api_request("POST", endpoint, data=params)
            finally:
                if original_version:
                    os.environ["INSTAGRAM_GRAPH_API_VERSION"] = original_version
                elif "INSTAGRAM_GRAPH_API_VERSION" in os.environ:
                    del os.environ["INSTAGRAM_GRAPH_API_VERSION"]
        else:
            result = make_api_request("POST", endpoint, data=params)
        
        return {
            "data": result,
            "error": "",
            "successful": True
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful guidance for common errors
        if "500" in error_msg or "internal server error" in error_msg.lower():
            error_msg += " This may indicate that the sender_action feature is not supported for your Instagram account or the specific recipient. The mark_seen feature may have limited support on Instagram."
        elif "permission" in error_msg.lower() or "#10" in error_msg:
            error_msg += " To fix: Generate a new token with 'instagram_manage_messages' permission from Graph API Explorer."
        elif "24" in error_msg.lower() or "messaging window" in error_msg.lower():
            error_msg += " The recipient must have an active 24-hour messaging window open. They need to message you first."
        
        return {
            "data": {},
            "error": f"Failed to mark messages as seen: {error_msg}",
            "successful": False
        }

# -------------------- MAIN --------------------

def parse_env_args():
    """Parse command line arguments for environment variables."""
    parser = argparse.ArgumentParser(description='Instagram MCP Server')
    parser.add_argument('--env', action='append', help='Environment variables in KEY=VALUE format')

    args = parser.parse_args()

    # Set environment variables from command line
    if args.env:
        for env_var in args.env:
            if '=' in env_var:
                key, value = env_var.split('=', 1)
                os.environ[key] = value
                print(f"Set environment variable: {key}")
            else:
                print(f"Warning: Invalid environment variable format: {env_var}")

if __name__ == "__main__":
    # Parse command line environment variables before running MCP
    parse_env_args()
    mcp.run()

def main():
    mcp.run()
