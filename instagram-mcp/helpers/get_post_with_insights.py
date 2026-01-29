#!/usr/bin/env python3
"""
Helper script: Get Post List with Insights
Gets list of posts and their insights in one go.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get the instagram-mcp directory (parent of helpers)
script_file = Path(__file__).resolve()
helpers_dir = script_file.parent
instagram_mcp_dir = helpers_dir.parent

# Add to Python path
if str(instagram_mcp_dir) not in sys.path:
    sys.path.insert(0, str(instagram_mcp_dir))

# Change to instagram-mcp directory for relative paths to work
os.chdir(instagram_mcp_dir)

# Load environment variables
env_path = instagram_mcp_dir / '.env'
if env_path.exists():
    load_dotenv(env_path)

from instagram_mcp_server import (
    INSTAGRAM_GET_IG_USER_MEDIA,
    INSTAGRAM_GET_IG_MEDIA_INSIGHTS
)

def main():
    """Get posts with their insights."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Instagram posts with insights')
    parser.add_argument('--limit', type=int, default=10, help='Number of posts (default: 10)')
    parser.add_argument('--metrics', nargs='+', default=['reach', 'likes', 'comments'], 
                       help='Insights metrics to retrieve')
    parser.add_argument('--ig_user_id', type=str, help='Instagram user ID (optional)')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("Getting Posts with Insights")
    print(f"{'='*60}\n")
    
    try:
        # Get posts
        print("Fetching posts...")
        posts_result = INSTAGRAM_GET_IG_USER_MEDIA(
            limit=args.limit,
            ig_user_id=args.ig_user_id
        )
        
        if not posts_result.get("successful"):
            print(f"Error: {posts_result.get('error')}")
            sys.exit(1)
        
        posts = posts_result.get("data", {}).get("data", [])
        print(f"Found {len(posts)} post(s)\n")
        
        # Get insights for each post
        results = []
        for i, post in enumerate(posts, 1):
            media_id = post.get("id")
            print(f"{i}. Post ID: {media_id}")
            print(f"   Caption: {post.get('caption', 'N/A')[:50]}...")
            
            # Get insights
            insights_result = INSTAGRAM_GET_IG_MEDIA_INSIGHTS(
                ig_media_id=media_id,
                metric=args.metrics,
                period="lifetime"
            )
            
            if insights_result.get("successful"):
                insights = insights_result.get("data", [])
                insights_dict = {}
                for insight in insights:
                    metric_name = insight.get("name")
                    values = insight.get("values", [])
                    if values:
                        insights_dict[metric_name] = values[0].get("value", "N/A")
                
                print("   Insights:")
                for metric, value in insights_dict.items():
                    print(f"     {metric}: {value}")
                
                results.append({
                    "post": post,
                    "insights": insights_dict
                })
            else:
                print(f"   Insights: {insights_result.get('error')}")
            
            print()
        
        print(f"{'='*60}")
        print("Complete!")
        print(f"{'='*60}\n")
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

