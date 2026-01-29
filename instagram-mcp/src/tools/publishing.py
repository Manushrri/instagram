"""
Instagram Media Publishing Tools

Tools for creating and publishing media content:
- Media containers (photos, videos, reels)
- Carousel posts
- Publishing and status checking
"""

import time
from typing import Optional, List, Dict, Any


def create_media_container(
    make_api_request,
    get_instagram_user_id,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
    caption: Optional[str] = None,
    media_type: Optional[str] = None,
    content_type: Optional[str] = None,
    cover_url: Optional[str] = None,
    is_carousel_item: bool = False,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a draft media container for photos/videos/reels before publishing.
    
    WORKFLOW:
    1. Call this to create a container
    2. Use GET_POST_STATUS to check when container is ready
    3. Use CREATE_POST or POST_IG_USER_MEDIA_PUBLISH to publish
    
    Returns: creation_id to use in subsequent calls
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        # Validate that either image_url or video_url is provided
        if not image_url and not video_url:
            raise ValueError("Either image_url or video_url must be provided")
        
        # Determine media type if not provided
        if not media_type:
            if video_url:
                media_type = "VIDEO"
            elif image_url:
                media_type = "IMAGE"
        else:
            media_type = media_type.upper()
            if media_type not in ["IMAGE", "VIDEO"]:
                raise ValueError(f"media_type must be 'IMAGE' or 'VIDEO', not '{media_type}'")
        
        params = {"media_type": media_type}
        
        if image_url:
            params["image_url"] = image_url
        if video_url:
            params["video_url"] = video_url
        if caption:
            params["caption"] = caption
        if content_type:
            params["content_type"] = content_type
        if cover_url:
            params["cover_url"] = cover_url
        if is_carousel_item:
            params["is_carousel_item"] = True
        
        response = make_api_request("POST", f"{user_id}/media", data=params)
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to create media container: {str(e)}",
            "successful": False
        }


def post_ig_user_media(
    make_api_request,
    get_instagram_user_id,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
    caption: Optional[str] = None,
    media_type: Optional[str] = None,
    cover_url: Optional[str] = None,
    is_carousel_item: Optional[bool] = None,
    children: Optional[List[str]] = None,
    location_id: Optional[str] = None,
    user_tags: Optional[List[Dict[str, Any]]] = None,
    thumb_offset: Optional[int] = None,
    share_to_feed: Optional[bool] = None,
    audio_name: Optional[str] = None,
    collaborators: Optional[List[str]] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Post IG User Media. Tool to create a media container for Instagram posts.
    Supports images, videos, Reels, or carousels.
    
    Returns: creation_id to use in subsequent calls
    """
    import json
    
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        # Validate inputs
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
        
        params = {"media_type": media_type}
        
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
        
        response = make_api_request("POST", f"{user_id}/media", data=params)
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to create media container: {str(e)}",
            "successful": False
        }


def create_carousel_container(
    make_api_request,
    get_instagram_user_id,
    children: Optional[List[str]] = None,
    child_image_urls: Optional[List[str]] = None,
    child_video_urls: Optional[List[str]] = None,
    caption: Optional[str] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a carousel (multi-image/video) post container.
    
    WORKFLOW:
    1. Create individual media containers with is_carousel_item=True
    2. Call this with the container IDs as 'children'
    3. Use CREATE_POST to publish the carousel
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        if children and (child_image_urls or child_video_urls):
            raise ValueError("Provide either children OR child_image_urls/child_video_urls, not both.")
        
        # Create child containers if URLs are provided
        if not children:
            child_image_urls = child_image_urls or []
            child_video_urls = child_video_urls or []
            if not child_image_urls and not child_video_urls:
                raise ValueError("Provide children or at least one child_image_urls/child_video_urls.")
            
            children = []
            
            # Create image child containers
            for url in child_image_urls:
                params = {"media_type": "IMAGE", "is_carousel_item": True, "image_url": url}
                result = make_api_request("POST", f"{user_id}/media", data=params)
                creation_id = result.get("id")
                if not creation_id:
                    raise ValueError("Failed to create child media container.")
                children.append(creation_id)
            
            # Create video child containers
            for url in child_video_urls:
                params = {"media_type": "VIDEO", "is_carousel_item": True, "video_url": url}
                result = make_api_request("POST", f"{user_id}/media", data=params)
                creation_id = result.get("id")
                if not creation_id:
                    raise ValueError("Failed to create child media container.")
                children.append(creation_id)
        
        params = {
            "media_type": "CAROUSEL",
            "children": ",".join(children)
        }
        
        if caption:
            params["caption"] = caption
        
        response = make_api_request("POST", f"{user_id}/media", data=params)
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to create carousel container: {str(e)}",
            "successful": False
        }


def get_post_status(
    make_api_request,
    creation_id: str,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check the status of a media container.
    
    STATUS VALUES:
    - EXPIRED: Container expired (24 hours)
    - ERROR: Processing failed
    - FINISHED: Ready to publish
    - IN_PROGRESS: Still processing
    - PUBLISHED: Already published
    """
    try:
        response = make_api_request(
            "GET",
            f"{creation_id}",
            params={"fields": "status_code"}
        )
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            return {
                "data": {},
                "error": f"Request timed out while checking post status. Try again in a few moments. Error: {error_msg}",
                "successful": False
            }
        return {
            "data": {},
            "error": f"Failed to get post status: {error_msg}",
            "successful": False
        }


def create_post(
    make_api_request,
    get_instagram_user_id,
    creation_id: str,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Publish a media container to Instagram.
    Automatically waits for container to be ready with exponential backoff.
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        # Check status first and wait if needed
        max_retries = 15
        retry_delay = 3
        
        for attempt in range(max_retries):
            status_data = make_api_request("GET", creation_id, params={"fields": "status_code"})
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
                retry_delay = min(retry_delay * 1.5, 10)
        
        # Publish the media
        response = make_api_request(
            "POST",
            f"{user_id}/media_publish",
            data={"creation_id": creation_id}
        )
        
        return {
            "data": response,
            "error": "",
            "successful": True
        }
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to create post: {str(e)}",
            "successful": False
        }


def post_ig_user_media_publish(
    make_api_request,
    get_instagram_user_id,
    creation_id: str,
    max_wait_seconds: int = 45,
    poll_interval_seconds: int = 3,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Publish a media container with automatic status polling.
    Automatically waits for container to finish processing.
    Rate limited to 25 posts per 24 hours.
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
        max_wait = min(max_wait_seconds or 45, 45)
        poll_interval = poll_interval_seconds or 3
        max_retries = max_wait // poll_interval if poll_interval > 0 else 15
        
        start_time = time.time()
        for attempt in range(max_retries):
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                return {
                    "data": {},
                    "error": f"Media container did not finish processing within {max_wait} seconds.",
                    "successful": False
                }
            
            status_data = make_api_request("GET", creation_id, params={"fields": "status_code"})
            status_code = status_data.get("status_code", "").upper()
            
            if status_code == "FINISHED":
                response = make_api_request(
                    "POST",
                    f"{user_id}/media_publish",
                    data={"creation_id": creation_id}
                )
                return {
                    "data": response,
                    "error": "",
                    "successful": True
                }
            elif status_code == "ERROR":
                return {
                    "data": status_data,
                    "error": f"Media container failed processing: {status_data.get('status', 'Unknown error')}",
                    "successful": False
                }
            elif status_code == "EXPIRED":
                return {
                    "data": status_data,
                    "error": "Media container has expired. Create a new one.",
                    "successful": False
                }
            elif status_code == "PUBLISHED":
                return {
                    "data": status_data,
                    "error": "",
                    "successful": True,
                    "message": "Media was already published"
                }
            
            time.sleep(poll_interval)
        
        return {
            "data": {"creation_id": creation_id},
            "error": f"Timeout after {max_wait}s. Use GET_POST_STATUS to check manually.",
            "successful": False
        }
        
    except Exception as e:
        return {
            "data": {},
            "error": f"Failed to publish media: {str(e)}",
            "successful": False
        }
