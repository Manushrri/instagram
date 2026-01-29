"""
Instagram User Tools

Tools for retrieving user profile information:
- User info and profile data
- User media feed
- Stories, tags, and live media
- Username lookup
"""

from typing import Optional, Dict, Any


def get_user_info(
    make_api_request,
    get_instagram_user_id,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get Instagram user profile information.
    
    Returns: username, name, biography, profile_picture_url, 
             followers_count, follows_count, media_count, website
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        response = make_api_request(
            "GET",
            f"{user_id}",
            params={
                "fields": "id,username,website,biography,profile_picture_url,followers_count,follows_count,media_count"
            }
        )
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        error_msg = str(e)
        if "nonexisting field" in error_msg.lower() or "#100" in error_msg:
            error_msg += " Note: Some fields may not be available for all account types."
        return {
            "data": {},
            "error": f"Failed to get user info: {error_msg}",
            "successful": False
        }


def get_user_media(
    make_api_request,
    get_instagram_user_id,
    limit: int = 25,
    after: Optional[str] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get Instagram user's media (posts, photos, videos).
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        params = {}
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        
        response = make_api_request("GET", f"{user_id}/media", params=params)
        
        return {
            "data": response.get("data", []),
            "paging": response.get("paging", {}),
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


def get_ig_user_media(
    make_api_request,
    get_instagram_user_id,
    fields: str = "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username",
    limit: int = 25,
    after: Optional[str] = None,
    before: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get Instagram user's media collection with custom fields and filtering.
    Returns media objects with 'id' field for use in other tools.
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
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
        
        response = make_api_request("GET", f"{user_id}/media", params=params)
        
        return {
            "data": response.get("data", []),
            "paging": response.get("paging", {}),
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


def get_ig_user_stories(
    make_api_request,
    get_instagram_user_id,
    fields: str = "id,media_type,media_url,permalink,timestamp",
    limit: Optional[int] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get active story media objects for an Instagram Business or Creator account.
    Note: Stories are only available for 24 hours after posting.
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        params = {
            "fields": fields or "id,media_type,media_url,permalink,timestamp"
        }
        
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        
        response = make_api_request("GET", f"{user_id}/stories", params=params)
        
        return {
            "data": response.get("data", []),
            "paging": response.get("paging", {}),
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


def get_ig_user_tags(
    make_api_request,
    get_instagram_user_id,
    fields: str = "id,caption,media_type,media_url,permalink,timestamp,username",
    limit: int = 25,
    after: Optional[str] = None,
    before: Optional[str] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get Instagram media where the user has been tagged by other users.
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        params = {
            "fields": fields or "id,caption,media_type,media_url,permalink,timestamp,username"
        }
        
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        
        response = make_api_request("GET", f"{user_id}/tags", params=params)
        
        return {
            "data": response.get("data", []),
            "paging": response.get("paging", {}),
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


def get_ig_user_content_publishing_limit(
    make_api_request,
    get_instagram_user_id,
    fields: str = "quota_usage,config",
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get an Instagram Business Account's current content publishing usage.
    Use this to monitor quota usage and avoid hitting rate limits.
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        response = make_api_request(
            "GET",
            f"{user_id}/content_publishing_limit",
            params={"fields": fields or "quota_usage,config"}
        )
        
        return {
            "data": response.get("data", []),
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": [],
            "error": f"Failed to get content publishing limit: {str(e)}",
            "successful": False
        }


def get_ig_user_live_media(
    make_api_request,
    get_instagram_user_id,
    fields: str = "id,media_type,media_url,timestamp,permalink",
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get live media objects during an active Instagram broadcast.
    Returns the live video media ID and metadata.
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        response = make_api_request(
            "GET",
            f"{user_id}/live_media",
            params={"fields": fields or "id,media_type,media_url,timestamp,permalink"}
        )
        
        return {
            "data": response.get("data", []),
            "paging": response.get("paging", {}),
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get live media: {str(e)}",
            "successful": False
        }


def get_user_by_username(
    make_api_request,
    get_instagram_user_id,
    username: str,
    ig_user_id: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find an Instagram user's ID by their username using Business Discovery API.
    IMPORTANT: Only works for Business or Creator accounts, not personal accounts.
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        # Remove @ if present
        clean_username = username.lstrip("@")
        
        response = make_api_request(
            "GET",
            f"{user_id}",
            params={
                "fields": f"business_discovery.username({clean_username}){{id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count}}"
            }
        )
        
        if "business_discovery" in response:
            user_info = response["business_discovery"]
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
