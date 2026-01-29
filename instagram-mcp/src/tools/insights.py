"""
Instagram Insights Tools

Tools for analytics and performance metrics:
- User account insights
- Post/media insights
- Engagement metrics
"""

from typing import Optional, List, Dict, Any


def get_user_insights(
    make_api_request,
    get_instagram_user_id,
    metric: List[str],
    period: str = "day",
    metric_type: Optional[str] = None,
    breakdown: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    timeframe: Optional[str] = None,
    graph_api_version: Optional[str] = None,
    ig_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get Instagram account-level insights and analytics.
    
    Valid metrics: reach, follower_count, website_clicks, profile_views,
    online_followers, accounts_engaged, total_interactions, views, etc.
    
    Note: 'impressions' is NOT valid for user insights (only for media insights).
    """
    try:
        user_id = get_instagram_user_id(ig_user_id)
        
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
        
        response = make_api_request("GET", f"{user_id}/insights", params=params)
        
        return {
            "data": response.get("data", []),
            "paging": response.get("paging", {}),
            "error": "",
            "successful": True
        }
    except Exception as e:
        error_msg = str(e)
        
        if "must be one of the following values" in error_msg.lower():
            error_msg += " Valid metrics: reach, follower_count, website_clicks, profile_views, online_followers, accounts_engaged, total_interactions, likes, comments, shares, saves, replies, views."
        elif "should be specified with parameter metric_type" in error_msg.lower():
            error_msg += " Solution: Some metrics require metric_type='total_value'. Make separate requests for different metric types."
        elif "permission" in error_msg.lower() or "#10" in error_msg:
            error_msg += " Generate a new token with 'instagram_manage_insights' permission."
        
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get user insights: {error_msg}",
            "successful": False
        }


def get_post_insights(
    make_api_request,
    ig_post_id: str,
    metric_preset: str = "auto_safe",
    metric: Optional[List[str]] = None,
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get Instagram post insights/analytics (reach, engagement, etc.).
    
    IMPORTANT: Only works for PUBLISHED posts, not container IDs.
    Use GET_USER_MEDIA to get published post IDs.
    """
    try:
        params = {}
        
        if metric:
            params["metric"] = ",".join(metric)
        else:
            params["metric_preset"] = metric_preset or "auto_safe"
        
        response = make_api_request("GET", f"{ig_post_id}/insights", params=params)
        
        return {
            "data": response.get("data", []),
            "paging": response.get("paging", {}),
            "error": "",
            "successful": True
        }
    except Exception as e:
        error_msg = str(e)
        
        if "impressions" in error_msg.lower() and "no longer supported" in error_msg.lower():
            error_msg += " Remove 'impressions' from metrics. Use 'reach' instead."
        elif "permission" in error_msg.lower() or "#10" in error_msg:
            error_msg += " Generate a new token with 'instagram_manage_insights' permission."
        
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get post insights: {error_msg}",
            "successful": False
        }


def get_ig_media_insights(
    make_api_request,
    ig_media_id: str,
    metric: List[str],
    period: str = "lifetime",
    graph_api_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get insights and metrics for Instagram media objects.
    
    IMPORTANT: In Graph API v22.0+, 'impressions' is no longer supported. Use 'reach' instead.
    Valid metrics: reach, likes, comments, shares, saved, video_views, plays, total_interactions, views, replies.
    
    Note: Insights data is only available for media published within the last 2 years.
    """
    try:
        # Auto-remove impressions for v22.0+ compatibility
        cleaned_metric = [m for m in metric if m != "impressions"]
        if len(cleaned_metric) < len(metric) and "reach" not in cleaned_metric:
            cleaned_metric.append("reach")
        
        params = {
            "metric": ",".join(cleaned_metric),
            "period": period or "lifetime"
        }
        
        response = make_api_request("GET", f"{ig_media_id}/insights", params=params)
        
        return {
            "data": response.get("data", []),
            "paging": response.get("paging", {}),
            "error": "",
            "successful": True
        }
    except Exception as e:
        error_msg = str(e)
        
        if "impressions" in error_msg.lower() and "no longer supported" in error_msg.lower():
            error_msg += " Remove 'impressions' from metrics. Use 'reach' instead."
        elif "metric" in error_msg.lower() and "must be one of" in error_msg.lower():
            error_msg += " Common valid metrics: reach, likes, comments, shares, saved, video_views, plays, total_interactions."
        elif "permission" in error_msg.lower() or "#10" in error_msg:
            error_msg += " Generate a new token with 'instagram_manage_insights' permission."
        
        return {
            "data": [],
            "paging": {},
            "error": f"Failed to get IG media insights: {error_msg}",
            "successful": False
        }
