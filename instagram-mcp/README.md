# Instagram MCP Server

A modular MCP (Model Context Protocol) server for Instagram Graph API. Provides 34 tools for posting, commenting, messaging, and analytics for Instagram Business and Creator accounts.

## Features

- 📸 **Publishing**: Create and publish photos, videos, reels, and carousels
- 💬 **Comments**: Read, post, reply to, and delete comments
- 📩 **Direct Messages**: Send text and images via DM
- 📊 **Analytics**: Get user and media insights
- 🔐 **OAuth2**: Automatic token storage and refresh (60-day tokens)
- 🧩 **Modular**: Clean separation of tools by category

## Project Structure

```
instagram-mcp/
├── main.py                 # Modular MCP server (recommended)
├── instagram_mcp_server.py # Original monolithic server
├── client.py               # Instagram API client
├── config.py               # Configuration settings
├── tools_manifest.json     # Tool definitions for dynamic loading
├── tools/                  # Modular tool implementations
│   ├── publishing.py       # 6 publishing tools
│   ├── user.py             # 8 user tools
│   ├── media.py            # 3 media tools
│   ├── comments.py         # 7 comment tools
│   ├── messaging.py        # 7 messaging tools
│   └── insights.py         # 3 insights tools
├── helpers/                # Standalone helper scripts
├── oauth_setup.py          # Automated OAuth setup
├── get_page_token.py       # Page token helper
└── .env                    # Your credentials (create this)
```

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -r instagram-mcp/requirements.txt

# Or using pip
pip install -r instagram-mcp/requirements.txt
```

### 2. Configure OAuth2

Create `instagram-mcp/.env`:

```env
OAUTH2_CLIENT_ID=your_facebook_app_id
OAUTH2_CLIENT_SECRET=your_facebook_app_secret
OAUTH2_REDIRECT_URI=http://localhost:8080/callback
```

### 3. Run OAuth Setup

```bash
uv run instagram-mcp/oauth_setup.py
```

This will:
1. Open your browser for Facebook login
2. Capture the authorization code
3. Exchange for long-lived token (60 days)
4. Save tokens to `.instagram_tokens.json`
5. Auto-refresh when expired

### 4. Run the Server

```bash
# Modular server (recommended)
uv run instagram-mcp/main.py

# Or original monolithic server
uv run instagram-mcp/instagram_mcp_server.py
```

## Available Tools (34 total)

### Publishing (6 tools)
| Tool | Description |
|------|-------------|
| `CREATE_MEDIA_CONTAINER` | Create draft container for photos/videos/reels |
| `POST_IG_USER_MEDIA` | Create media container with full options |
| `CREATE_CAROUSEL_CONTAINER` | Create multi-image carousel post |
| `GET_POST_STATUS` | Check container processing status |
| `CREATE_POST` | Publish a media container |
| `POST_IG_USER_MEDIA_PUBLISH` | Publish with automatic status polling |

### User (8 tools)
| Tool | Description |
|------|-------------|
| `GET_USER_INFO` | Get profile information |
| `GET_USER_MEDIA` | Get user's recent posts |
| `GET_IG_USER_MEDIA` | Get media with custom fields |
| `GET_IG_USER_STORIES` | Get active stories |
| `GET_IG_USER_TAGS` | Get media where user is tagged |
| `GET_IG_USER_CONTENT_PUBLISHING_LIMIT` | Check rate limit status |
| `GET_IG_USER_LIVE_MEDIA` | Get live broadcast media |
| `GET_USER_BY_USERNAME` | Look up user by username |

### Media (3 tools)
| Tool | Description |
|------|-------------|
| `GET_IG_MEDIA` | Get media details |
| `GET_IG_MEDIA_CHILDREN` | Get carousel children |
| `GET_IG_MEDIA_COMMENTS` | Get comments on media |

### Comments (7 tools)
| Tool | Description |
|------|-------------|
| `GET_POST_COMMENTS` | Get comments on a post |
| `POST_IG_MEDIA_COMMENTS` | Post a comment |
| `POST_IG_COMMENT_REPLIES` | Reply to a comment |
| `POST_IG_USER_MENTIONS` | Reply to @mentions |
| `REPLY_TO_COMMENT` | Reply to a comment |
| `GET_IG_COMMENT_REPLIES` | Get replies to a comment |
| `DELETE_COMMENT` | Delete a comment |

### Messaging (7 tools)
| Tool | Description |
|------|-------------|
| `GET_CONVERSATION` | Get conversation details |
| `GET_CONVERSATIONS` | List all conversations |
| `LIST_ALL_CONVERSATIONS` | List conversations (simplified) |
| `LIST_ALL_MESSAGES` | Get messages in a conversation |
| `SEND_TEXT_MESSAGE` | Send a text DM |
| `SEND_IMAGE` | Send an image DM |
| `MARK_SEEN` | Mark messages as read |

### Insights (3 tools)
| Tool | Description |
|------|-------------|
| `GET_USER_INSIGHTS` | Get account analytics |
| `GET_POST_INSIGHTS` | Get post metrics |
| `GET_IG_MEDIA_INSIGHTS` | Get media insights |

## OAuth Token System

Facebook/Instagram uses a unique token system:

```
┌─────────────────────────────────────────────────────────────┐
│                   TOKEN LIFECYCLE                           │
├─────────────────────────────────────────────────────────────┤
│  Day 0:   OAuth setup → 60-day token saved                  │
│  Day 55:  Auto-refresh triggered → New 60-day token         │
│  Day 115: Auto-refresh again → Continues indefinitely       │
└─────────────────────────────────────────────────────────────┘
```

**Key points:**
- No separate refresh token - the access_token IS the refresh token
- Tokens last 60 days and auto-refresh 5 minutes before expiry
- Tokens stored in `.instagram_tokens.json` (git-ignored)

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OAUTH2_CLIENT_ID` | Yes | Facebook App ID |
| `OAUTH2_CLIENT_SECRET` | Yes | Facebook App Secret |
| `OAUTH2_REDIRECT_URI` | No | Default: `http://localhost:8080/callback` |
| `INSTAGRAM_USER_ID` | No | Auto-detected from token |
| `FACEBOOK_PAGE_ID` | No | Auto-detected, recommended for messaging |
| `INSTAGRAM_GRAPH_API_VERSION` | No | Default: `v21.0` |

### Token Storage

Tokens are stored in `.instagram_tokens.json`:

```json
{
  "access_token": "EAAT...",
  "access_token_saved_at": 1769625471,
  "page_access_token": "EAAT...",
  "facebook_page_id": "958164070712594",
  "expires_in": 5184000
}
```

## Usage Examples

### Create and Publish a Photo

```json
// Step 1: Create container
CREATE_MEDIA_CONTAINER
{
  "image_url": "https://example.com/photo.jpg",
  "caption": "Hello Instagram! #mcp",
  "media_type": "IMAGE"
}

// Step 2: Publish (uses creation_id from step 1)
CREATE_POST
{
  "creation_id": "17889455560051444"
}
```

### Get User's Posts

```json
GET_USER_MEDIA
{
  "limit": 10
}
```

### Send a DM

```json
SEND_TEXT_MESSAGE
{
  "recipient_id": "17841400000000000",
  "text": "Hello from MCP!"
}
```

## Messaging Limitations

⚠️ **24-Hour Window Policy:**
- Recipients must message you FIRST before you can reply
- Use `LIST_ALL_CONVERSATIONS` to find active conversations
- App Review required to initiate conversations

## Helper Scripts

Run standalone scripts for common tasks:

```bash
# Get list of recent posts
uv run instagram-mcp/helpers/get_post_list.py

# Publish a post
uv run instagram-mcp/helpers/publish_post.py --image-url "https://..." --caption "Hello!"

# Get post insights
uv run instagram-mcp/helpers/get_post_insights.py --post-id "17889..."

# Get conversations with messages
uv run instagram-mcp/helpers/get_conversations_with_messages.py
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `Invalid OAuth access token` | Run `oauth_setup.py` again |
| `Media not ready` | Wait a few seconds, use `GET_POST_STATUS` |
| `Rate limit exceeded` | Max 25 posts per 24 hours |
| `Personal account not supported` | Switch to Business/Creator account |
| `Page not found` | Connect Instagram to a Facebook Page |
| `Error (#3) Capability` | Recipient must message you first |
| `Error (#190) Page Access Token` | Run `get_page_token.py` |

## MCP Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "instagram": {
      "command": "uv",
      "args": ["run", "instagram-mcp/main.py"],
      "cwd": "/path/to/instagram"
    }
  }
}
```

## Requirements

- Python 3.10+
- Instagram Business or Creator account
- Facebook App with Instagram permissions
- Account connected to a Facebook Page

## License

MIT License
