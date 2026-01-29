"""
Instagram Messaging Tools

Tools for Instagram Direct Messages:
- Listing conversations
- Reading messages
- Sending messages and images
- Marking as seen
"""

import os
from typing import Optional, Dict, Any


def get_conversation(
    make_api_request,
    get_page_for_ig_account,
    get_instagram_user_id,
    conversation_id: str,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get details about a specific Instagram DM conversation (participants, etc).
    Requires Page Access Token (automatically used).
    """
    try:
        ig_user_id = get_instagram_user_id(None)
        page_info = get_page_for_ig_account(ig_user_id)
        page_access_token = page_info.get("page_access_token")
        
        if not page_info.get("page_id"):
            raise ValueError("Could not find Facebook Page ID. Connect your Instagram account to a Facebook Page or set FACEBOOK_PAGE_ID.")
        
        if not page_access_token:
            raise ValueError("Page Access Token is required. Run: uv run instagram-mcp/get_page_token.py")
        
        # Temporarily use page token
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_access_token
        
        try:
            params = {"fields": "id,participants,updated_time"}
            response = make_api_request("GET", conversation_id, params=params)
            
            return {
                "data": response,
                "error": "",
                "successful": True
            }
        finally:
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
                
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to get conversation: {str(e)}",
            "successful": False
        }


def get_conversations(
    make_api_request,
    get_page_for_ig_account,
    get_instagram_user_id,
    page_id: Optional[str] = None,
    limit: Optional[int] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List Instagram DM conversations to find conversation IDs.
    Returns conversation objects with 'id' field and 'participants' array.
    """
    try:
        ig_user_id = get_instagram_user_id(None)
        page_info = get_page_for_ig_account(ig_user_id)
        
        if page_id:
            page_info["page_id"] = page_id
        
        page_id_value = page_info.get("page_id")
        page_access_token = page_info.get("page_access_token")
        
        if not page_id_value:
            raise ValueError("Could not find Facebook Page ID. Set FACEBOOK_PAGE_ID.")
        
        if not page_access_token:
            raise ValueError("Page Access Token is required. Run: uv run instagram-mcp/get_page_token.py")
        
        # Use page token
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_access_token
        
        try:
            params = {
                "platform": "instagram",
                "fields": "id,participants,updated_time"
            }
            if limit:
                params["limit"] = limit
            
            response = make_api_request("GET", f"{page_id_value}/conversations", params=params)
            
            return {
                "data": response,
                "error": "",
                "successful": True
            }
        finally:
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
                
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to get conversations: {str(e)}",
            "successful": False
        }


def list_all_conversations(
    make_api_request,
    get_page_for_ig_account,
    get_instagram_user_id,
    load_tokens,
    limit: int = 25,
    after: Optional[str] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all Instagram DM conversations for the authenticated user.
    This is the recommended function for getting conversations.
    """
    try:
        # Load stored tokens
        stored_tokens = load_tokens()
        page_token = stored_tokens.get("page_access_token")
        page_id = stored_tokens.get("facebook_page_id")
        
        # Fall back to environment variables
        if not page_token:
            page_token = os.environ.get("INSTAGRAM_PAGE_ACCESS_TOKEN")
        if not page_id:
            page_id = os.environ.get("FACEBOOK_PAGE_ID")
        
        # Try auto-detection as last resort
        if not page_token or not page_id:
            user_id = get_instagram_user_id(ig_user_id)
            page_info = get_page_for_ig_account(user_id)
            if not page_token:
                page_token = page_info.get("page_access_token")
            if not page_id:
                page_id = page_info.get("page_id")
        
        if not page_token:
            return {
                "data": [],
                "paging": {},
                "error": "Page Access Token is required. Run: uv run instagram-mcp/get_page_token.py",
                "successful": False
            }
        
        if not page_id:
            return {
                "data": [],
                "paging": {},
                "error": "Facebook Page ID not found. Ensure Instagram is connected to a Facebook Page.",
                "successful": False
            }
        
        # Use page token
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_token
        
        try:
            params = {
                "platform": "instagram",
                "fields": "id,participants,updated_time",
                "limit": limit
            }
            
            if after:
                params["after"] = after
            
            response = make_api_request("GET", f"{page_id}/conversations", params=params)
            
            conversations_data = response.get("data", [])
            
            if not conversations_data:
                return {
                    "data": [],
                    "paging": response.get("paging", {}),
                    "error": "No conversations found.",
                    "successful": True
                }
            
            return {
                "data": conversations_data,
                "paging": response.get("paging", {}),
                "error": "",
                "successful": True
            }
        finally:
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
                
    except Exception as e:
        error_msg = str(e)
        if "permission" in error_msg.lower() or "access" in error_msg.lower():
            error_msg += " Ensure your access token has 'pages_messaging' permission."
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to list conversations: {error_msg}",
            "successful": False
        }


def list_all_messages(
    make_api_request,
    get_page_for_ig_account,
    get_instagram_user_id,
    conversation_id: str,
    limit: int = 25,
    after: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all messages from a specific Instagram DM conversation.
    """
    try:
        ig_user_id = get_instagram_user_id(None)
        page_info = get_page_for_ig_account(ig_user_id)
        page_token = page_info.get("page_access_token")
        
        if not page_token:
            return {
                "data": [],
                "paging": {},
                "error": "Page Access Token required. Run: uv run instagram-mcp/get_page_token.py",
                "successful": False
            }
        
        # Use page token
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_token
        
        try:
            params = {
                "fields": "id,message,from,created_time,attachments",
                "limit": limit
            }
            
            if after:
                params["after"] = after
            
            response = make_api_request("GET", f"{conversation_id}/messages", params=params)
            
            return {
                "data": response.get("data", []),
                "paging": response.get("paging", {}),
                "error": "",
                "successful": True
            }
        finally:
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
                
    except Exception as e:
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to list messages: {str(e)}",
            "successful": False
        }


def send_text_message(
    make_api_request,
    get_page_for_ig_account,
    get_instagram_user_id,
    recipient_id: str,
    text: str,
    ig_user_id: Optional[str] = None,
    reply_to_message_id: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a text message to an Instagram user via DM.
    Note: Can only message users who have messaged you first or interacted with your content.
    """
    import json as json_module
    
    try:
        user_id = get_instagram_user_id(ig_user_id)
        page_info = get_page_for_ig_account(user_id)
        page_token = page_info.get("page_access_token")
        
        if not page_token:
            return {
                "data": {},
                "error": "Page Access Token required. Run: uv run instagram-mcp/get_page_token.py",
                "successful": False
            }
        
        # Use page token
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_token
        
        try:
            params = {
                "recipient": json_module.dumps({"id": recipient_id}),
                "message": json_module.dumps({"text": text})
            }
            
            if reply_to_message_id:
                params["message"] = json_module.dumps({"text": text, "reply_to": {"message_id": reply_to_message_id}})
            
            response = make_api_request("POST", f"{user_id}/messages", data=params)
            
            return {
                "data": response,
                "error": "",
                "successful": True
            }
        finally:
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
                
    except Exception as e:
        error_msg = str(e)
        if "(#3)" in error_msg or "does not have the capability" in error_msg.lower():
            error_msg += " The recipient must message you first."
        elif "(#100)" in error_msg:
            error_msg += " The recipient hasn't messaged you first or recipient_id is incorrect."
        elif "permission" in error_msg.lower():
            error_msg += " Ensure 'pages_messaging' and 'instagram_manage_messages' permissions."
        
        return {
            "data": {},
            "error": f"Failed to send text message: {error_msg}",
            "successful": False
        }


def send_image(
    make_api_request,
    get_page_for_ig_account,
    get_instagram_user_id,
    recipient_id: str,
    image_url: str,
    ig_user_id: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send an image via Instagram DM to a specific user.
    """
    import json as json_module
    
    try:
        user_id = get_instagram_user_id(ig_user_id)
        page_info = get_page_for_ig_account(user_id)
        page_token = page_info.get("page_access_token")
        
        if not page_token:
            return {
                "data": {},
                "error": "Page Access Token required. Run: uv run instagram-mcp/get_page_token.py",
                "successful": False
            }
        
        # Use page token
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_token
        
        try:
            params = {
                "recipient": json_module.dumps({"id": recipient_id}),
                "message": json_module.dumps({"attachment": {"type": "image", "payload": {"url": image_url}}})
            }
            
            response = make_api_request("POST", f"{user_id}/messages", data=params)
            
            return {
                "data": response,
                "error": "",
                "successful": True
            }
        finally:
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
                
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to send image: {str(e)}",
            "successful": False
        }


def mark_seen(
    make_api_request,
    get_page_for_ig_account,
    get_instagram_user_id,
    recipient_id: str,
    ig_user_id: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mark Instagram DM messages as read/seen for a specific user.
    """
    import json as json_module
    
    try:
        user_id = get_instagram_user_id(ig_user_id)
        page_info = get_page_for_ig_account(user_id)
        page_token = page_info.get("page_access_token")
        
        if not page_token:
            return {
                "data": {},
                "error": "Page Access Token required. Run: uv run instagram-mcp/get_page_token.py",
                "successful": False
            }
        
        # Use page token
        original_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = page_token
        
        try:
            params = {
                "recipient": json_module.dumps({"id": recipient_id}),
                "sender_action": "mark_seen"
            }
            
            response = make_api_request("POST", f"{user_id}/messages", data=params)
            
            return {
                "data": response,
                "error": "",
                "successful": True
            }
        finally:
            if original_token:
                os.environ["INSTAGRAM_ACCESS_TOKEN"] = original_token
            elif "INSTAGRAM_ACCESS_TOKEN" in os.environ:
                del os.environ["INSTAGRAM_ACCESS_TOKEN"]
                
    except Exception as e:
        error_msg = str(e)
        if "500" in error_msg or "internal server error" in error_msg.lower():
            error_msg += " The sender_action feature may not be supported for this account."
        elif "permission" in error_msg.lower():
            error_msg += " Generate a token with 'instagram_manage_messages' permission."
        
        return {
            "data": {},
            "error": f"Failed to mark messages as seen: {error_msg}",
            "successful": False
        }
