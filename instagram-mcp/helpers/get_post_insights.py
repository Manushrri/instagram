#!/usr/bin/env python3
"""
Helper script: Get Post Insights
Gets insights/analytics for a published Instagram post.
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

from instagram_mcp_server import INSTAGRAM_GET_IG_MEDIA_INSIGHTS

def main():
    """Get insights for an Instagram post."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get insights for an Instagram post')
    parser.add_argument('--media_id', type=str, required=True, help='Published media ID (get from GET_USER_MEDIA or after publishing)')
    parser.add_argument('--metrics', nargs='+', default=['reach', 'likes', 'comments', 'shares', 'saved'], 
                       help='Metrics to retrieve (default: reach likes comments shares saved)')
    parser.add_argument('--period', type=str, default='lifetime', choices=['lifetime', 'day'], 
                       help='Time period (default: lifetime)')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("Getting Post Insights")
    print(f"{'='*60}\n")
    print(f"Media ID: {args.media_id}")
    print(f"Metrics: {', '.join(args.metrics)}")
    print(f"Period: {args.period}\n")
    
    try:
        result = INSTAGRAM_GET_IG_MEDIA_INSIGHTS(
            ig_media_id=args.media_id,
            metric=args.metrics,
            period=args.period
        )
        
        if result.get("successful"):
            insights = result.get("data", [])
            
            if not insights:
                print("No insights data returned.")
                return
            
            print("Insights:")
            print(f"{'='*60}")
            for insight in insights:
                metric_name = insight.get("name", "N/A")
                values = insight.get("values", [])
                
                if values:
                    value = values[0].get("value", "N/A")
                    print(f"{metric_name}: {value}")
                else:
                    print(f"{metric_name}: No data")
            print(f"{'='*60}\n")
            
            return insights
        else:
            print(f"Error: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

