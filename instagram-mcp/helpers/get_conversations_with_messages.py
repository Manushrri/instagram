#!/usr/bin/env python3
"""
Helper script: Get Conversations with Messages
Gets all conversations and their recent messages.
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
    INSTAGRAM_LIST_ALL_CONVERSATIONS,
    INSTAGRAM_LIST_ALL_MESSAGES
)

def main():
    """Get conversations with their messages."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Instagram conversations with messages')
    parser.add_argument('--limit', type=int, default=10, help='Number of conversations (default: 10)')
    parser.add_argument('--messages_per_conv', type=int, default=5, help='Messages per conversation (default: 5)')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("Getting Conversations with Messages")
    print(f"{'='*60}\n")
    
    try:
        # Get conversations
        print("Fetching conversations...")
        convs_result = INSTAGRAM_LIST_ALL_CONVERSATIONS(limit=args.limit)
        
        if not convs_result.get("successful"):
            print(f"Error: {convs_result.get('error')}")
            sys.exit(1)
        
        conversations = convs_result.get("data", [])
        print(f"Found {len(conversations)} conversation(s)\n")
        
        # Get messages for each conversation
        results = []
        for i, conv in enumerate(conversations, 1):
            conv_id = conv.get("id")
            participants = conv.get("participants", {}).get("data", [])
            
            print(f"{i}. Conversation ID: {conv_id}")
            print(f"   Participants: {len(participants)}")
            for participant in participants:
                print(f"     - {participant.get('id')}")
            
            # Get messages
            messages_result = INSTAGRAM_LIST_ALL_MESSAGES(
                conversation_id=conv_id,
                limit=args.messages_per_conv
            )
            
            if messages_result.get("successful"):
                messages = messages_result.get("data", [])
                print(f"   Messages ({len(messages)}):")
                for msg in messages:
                    text = msg.get("message", "N/A")
                    from_user = msg.get("from", {}).get("id", "N/A")
                    print(f"     [{from_user}]: {text[:50]}...")
                
                results.append({
                    "conversation": conv,
                    "messages": messages
                })
            else:
                print(f"   Messages: {messages_result.get('error')}")
            
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

