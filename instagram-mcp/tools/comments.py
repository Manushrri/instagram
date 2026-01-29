"""
Instagram Comments Tools

Tools for managing comments:
- Reading comments and replies
- Posting comments and replies
- Deleting comments
- Handling mentions
"""

from typing import Optional, Dict, Any


def get_post_comments(
    make_api_request,
    ig_post_id: str,
    limit: int = 25,
    after: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get comments on an Instagram post.
    Returns comment objects with 'id' field for use in POST_IG_COMMENT_REPLIES or DELETE_COMMENT.
    """
    try:
        params = {}
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        
        response = make_api_request("GET", f"{ig_post_id}/comments", params=params)
        
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
            "error": f"Failed to get post comments: {str(e)}",
            "successful": False
        }


def post_ig_media_comments(
    make_api_request,
    ig_media_id: str,
    message: str,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a comment on an Instagram media object.
    Comment must be 300 characters or less, max 4 hashtags, max 1 URL.
    """
    try:
        response = make_api_request(
            "POST",
            f"{ig_media_id}/comments",
            data={"message": message}
        )
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to post media comment: {str(e)}",
            "successful": False
        }


def post_ig_comment_replies(
    make_api_request,
    ig_comment_id: str,
    message: str,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a reply to an Instagram comment.
    Reply must be 300 characters or less, max 4 hashtags, max 1 URL.
    """
    try:
        response = make_api_request(
            "POST",
            f"{ig_comment_id}/replies",
            data={"message": message}
        )
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to post comment reply: {str(e)}",
            "successful": False
        }


def post_ig_user_mentions(
    make_api_request,
    get_instagram_user_id,
    media_id: str,
    message: str,
    comment_id: Optional[str] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reply to a mention of your Instagram Business or Creator account.
    Creates a comment on the media or comment containing the mention.
    """
    try:
        ig_user_id = get_instagram_user_id(ig_user_id)
        
        # If comment_id is provided, reply to the comment. Otherwise, comment on the media.
        if comment_id:
            endpoint = f"{comment_id}/replies"
        else:
            endpoint = f"{media_id}/comments"
        
        response = make_api_request("POST", endpoint, data={"message": message})
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to reply to mention: {str(e)}",
            "successful": False
        }


def reply_to_comment(
    make_api_request,
    ig_comment_id: str,
    message: str,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reply to a comment on Instagram media.
    """
    try:
        response = make_api_request(
            "POST",
            f"{ig_comment_id}/replies",
            data={"message": message}
        )
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to reply to comment: {str(e)}",
            "successful": False
        }


def get_ig_comment_replies(
    make_api_request,
    ig_comment_id: str,
    fields: Optional[str] = None,
    limit: int = 25,
    after: Optional[str] = None,
    before: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get replies to a specific Instagram comment.
    """
    try:
        params = {
            "fields": fields or "id,text,username,timestamp,like_count,hidden,from,media,parent_id,legacy_instagram_comment_id"
        }
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        
        response = make_api_request("GET", f"{ig_comment_id}/replies", params=params)
        
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
            "error": f"Failed to get comment replies: {str(e)}",
            "successful": False
        }


def delete_comment(
    make_api_request,
    ig_comment_id: str,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delete a comment on Instagram media.
    You can only delete comments that your account created.
    """
    try:
        response = make_api_request("DELETE", ig_comment_id)
        
        return {
            "data": response if response else {"success": True},
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to delete comment: {str(e)}",
            "successful": False
        }
