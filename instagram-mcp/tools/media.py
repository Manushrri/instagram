"""
Instagram Media Tools

Tools for retrieving media information:
- Single media details
- Carousel children
- Media comments
"""

from typing import Optional, Dict, Any


def get_ig_media(
    make_api_request,
    ig_media_id: str,
    fields: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a published Instagram Media object (photo, video, story, reel, or carousel).
    NOTE: This is for published media only. For unpublished containers, use GET_POST_STATUS.
    """
    try:
        params = {
            "fields": fields or "id"
        }
        
        response = make_api_request("GET", ig_media_id, params=params)
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to get IG media: {str(e)}",
            "successful": False
        }


def get_ig_media_children(
    make_api_request,
    ig_media_id: str,
    fields: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get media objects (images/videos) that are children of an Instagram carousel/album post.
    Note: Carousel children do not support insights queries.
    """
    try:
        params = {
            "fields": fields or "id,media_type,media_url,permalink,timestamp"
        }
        
        response = make_api_request("GET", f"{ig_media_id}/children", params=params)
        
        return {
            "data": response.get("data", []),
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": [],
            "error": f"Failed to get media children: {str(e)}",
            "successful": False
        }


def get_ig_media_comments(
    make_api_request,
    ig_media_id: str,
    fields: Optional[str] = None,
    limit: int = 25,
    after: Optional[str] = None,
    before: Optional[str] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve comments on an Instagram media object.
    Returns comment objects with 'id' field for use in POST_IG_COMMENT_REPLIES or DELETE_COMMENT.
    """
    try:
        params = {
            "fields": fields or "id,text,username,timestamp,like_count,from,hidden,media,parent_id"
        }
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        
        response = make_api_request("GET", f"{ig_media_id}/comments", params=params)
        
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
            "error": f"Failed to get media comments: {str(e)}",
            "successful": False
        }
