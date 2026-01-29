#!/usr/bin/env python3
"""
Helper script: Get Post List
Gets a list of all published Instagram posts with their details.
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

from instagram_mcp_server import INSTAGRAM_GET_IG_USER_MEDIA

def main():
    """Get list of Instagram posts."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get list of Instagram posts')
    parser.add_argument('--limit', type=int, default=25, help='Number of posts to retrieve (default: 25)')
    parser.add_argument('--after', type=str, help='Paging cursor for next page')
    parser.add_argument('--ig_user_id', type=str, help='Instagram user ID (optional, auto-detected if not provided)')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("Getting Instagram Posts")
    print(f"{'='*60}\n")
    
    try:
        result = INSTAGRAM_GET_IG_USER_MEDIA(
            limit=args.limit,
            after=args.after,
            ig_user_id=args.ig_user_id
        )
        
        if result.get("successful"):
            posts = result.get("data", {}).get("data", [])
            paging = result.get("data", {}).get("paging", {})
            
            print(f"Found {len(posts)} post(s):\n")
            
            for i, post in enumerate(posts, 1):
                print(f"{i}. Post ID: {post.get('id')}")
                print(f"   Type: {post.get('media_type', 'N/A')}")
                print(f"   Caption: {post.get('caption', 'N/A')[:50]}...")
                print(f"   Timestamp: {post.get('timestamp', 'N/A')}")
                print()
            
            if paging.get("cursors", {}).get("after"):
                print(f"Next page cursor: {paging['cursors']['after']}")
                print("Use --after with this cursor to get more posts")
            
            print(f"\n{'='*60}")
            print("Success! Use the Post IDs above for insights, comments, etc.")
            print(f"{'='*60}\n")
            
            return posts
        else:
            print(f"Error: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

