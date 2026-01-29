#!/usr/bin/env python3
"""
Helper script: Publish Post
Complete workflow: Create media container and publish it.
"""

import os
import sys
import time
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
    INSTAGRAM_CREATE_MEDIA_CONTAINER,
    INSTAGRAM_GET_POST_STATUS,
    INSTAGRAM_CREATE_POST
)

def main():
    """Publish a post to Instagram."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Publish a post to Instagram')
    parser.add_argument('--image_url', type=str, required=True, help='Image URL for the post')
    parser.add_argument('--caption', type=str, help='Caption for the post')
    parser.add_argument('--wait', action='store_true', help='Wait for processing before publishing')
    parser.add_argument('--ig_user_id', type=str, help='Instagram user ID (optional)')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("Publishing Instagram Post")
    print(f"{'='*60}\n")
    
    try:
        # Step 1: Create media container
        print("Step 1: Creating media container...")
        container_result = INSTAGRAM_CREATE_MEDIA_CONTAINER(
            image_url=args.image_url,
            caption=args.caption,
            media_type="IMAGE",
            ig_user_id=args.ig_user_id
        )
        
        if not container_result.get("successful"):
            print(f"Error creating container: {container_result.get('error')}")
            sys.exit(1)
        
        creation_id = container_result.get("data", {}).get("id")
        print(f"Container created: {creation_id}\n")
        
        # Step 2: Wait for processing if requested
        if args.wait:
            print("Step 2: Waiting for media to process...")
            max_wait = 60
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_result = INSTAGRAM_GET_POST_STATUS(creation_id)
                if status_result.get("successful"):
                    status_code = status_result.get("data", {}).get("status_code")
                    print(f"Status: {status_code}")
                    
                    if status_code == "FINISHED":
                        print("Media is ready!\n")
                        break
                    elif status_code == "ERROR":
                        print("Error: Media processing failed")
                        sys.exit(1)
                
                time.sleep(3)
        
        # Step 3: Publish
        print("Step 3: Publishing post...")
        publish_result = INSTAGRAM_CREATE_POST(
            creation_id=creation_id,
            ig_user_id=args.ig_user_id
        )
        
        if publish_result.get("successful"):
            media_id = publish_result.get("data", {}).get("id")
            print(f"\n{'='*60}")
            print("Post published successfully!")
            print(f"{'='*60}")
            print(f"Published Media ID: {media_id}")
            print(f"\nYou can now use this ID for:")
            print(f"  - GET_IG_MEDIA_INSIGHTS")
            print(f"  - GET_IG_MEDIA_COMMENTS")
            print(f"  - GET_IG_MEDIA")
            print(f"{'='*60}\n")
            return media_id
        else:
            print(f"Error publishing: {publish_result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

