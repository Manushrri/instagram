"""
Instagram MCP Tools Package

This package contains all Instagram API tool functions organized by category.
"""

# Publishing Tools
from .publishing import (
    create_media_container,
    post_ig_user_media,
    create_carousel_container,
    get_post_status,
    create_post,
    post_ig_user_media_publish,
)

# User Tools
from .user import (
    get_user_info,
    get_user_media,
    get_ig_user_media,
    get_ig_user_stories,
    get_ig_user_tags,
    get_ig_user_content_publishing_limit,
    get_ig_user_live_media,
    get_user_by_username,
)

# Media Tools
from .media import (
    get_ig_media,
    get_ig_media_children,
    get_ig_media_comments,
)

# Comments Tools
from .comments import (
    get_post_comments,
    post_ig_media_comments,
    post_ig_comment_replies,
    post_ig_user_mentions,
    reply_to_comment,
    get_ig_comment_replies,
    delete_comment,
)

# Messaging Tools
from .messaging import (
    get_conversation,
    get_conversations,
    list_all_conversations,
    list_all_messages,
    send_text_message,
    send_image,
    mark_seen,
)

# Insights Tools
from .insights import (
    get_user_insights,
    get_post_insights,
    get_ig_media_insights,
)

__all__ = [
    # Publishing
    "create_media_container",
    "post_ig_user_media",
    "create_carousel_container",
    "get_post_status",
    "create_post",
    "post_ig_user_media_publish",
    # User
    "get_user_info",
    "get_user_media",
    "get_ig_user_media",
    "get_ig_user_stories",
    "get_ig_user_tags",
    "get_ig_user_content_publishing_limit",
    "get_ig_user_live_media",
    "get_user_by_username",
    # Media
    "get_ig_media",
    "get_ig_media_children",
    "get_ig_media_comments",
    # Comments
    "get_post_comments",
    "post_ig_media_comments",
    "post_ig_comment_replies",
    "post_ig_user_mentions",
    "reply_to_comment",
    "get_ig_comment_replies",
    "delete_comment",
    # Messaging
    "get_conversation",
    "get_conversations",
    "list_all_conversations",
    "list_all_messages",
    "send_text_message",
    "send_image",
    "mark_seen",
    # Insights
    "get_user_insights",
    "get_post_insights",
    "get_ig_media_insights",
]
