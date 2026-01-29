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
├── .instagram_tokens.json  # Saved tokens (auto-generated)
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
# REQUIRED - Get from Facebook Developer App
OAUTH2_CLIENT_ID=your_facebook_app_id
OAUTH2_CLIENT_SECRET=your_facebook_app_secret
OAUTH2_REDIRECT_URI=http://localhost:8080/callback

# OPTIONAL - These are ALL auto-detected, no need to set!
# INSTAGRAM_USER_ID=auto-detected
# FACEBOOK_PAGE_ID=auto-detected
# INSTAGRAM_PAGE_ACCESS_TOKEN=auto-detected
# INSTAGRAM_GRAPH_API_VERSION=v21.0 (default)
```

### 3. Run OAuth Setup

```bash
uv run instagram-mcp/oauth_setup.py
```

### 4. Run the Server

```bash
# Modular server (recommended)
uv run instagram-mcp/main.py

# Or original monolithic server
uv run instagram-mcp/instagram_mcp_server.py
```

---

## Complete Token & ID Guide

### What You Need to Know

**You DON'T need to manually set any IDs!** Everything is auto-detected when you run `oauth_setup.py`.

### The Complete OAuth Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 1: Run oauth_setup.py                               │
│                    $ uv run instagram-mcp/oauth_setup.py                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Browser Opens                                                      │
│  - You log into Facebook                                                    │
│  - You authorize the app                                                    │
│  - Facebook redirects with ?code=XXXXX                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Exchange Code for SHORT-LIVED Token                                │
│                                                                             │
│  POST https://graph.facebook.com/oauth/access_token                         │
│    ?client_id={app_id}                                                      │
│    &client_secret={app_secret}                                              │
│    &code={authorization_code}                                               │
│                                                                             │
│  Returns: short_lived_access_token (valid 1-2 hours)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Exchange for LONG-LIVED Token (60 days)                            │
│                                                                             │
│  GET https://graph.facebook.com/oauth/access_token                          │
│    ?grant_type=fb_exchange_token                                            │
│    &client_id={app_id}                                                      │
│    &client_secret={app_secret}                                              │
│    &fb_exchange_token={short_lived_token}                                   │
│                                                                             │
│  Returns: access_token (valid 60 days)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Get Page Access Token & IDs                                        │
│                                                                             │
│  GET https://graph.facebook.com/me/accounts                                 │
│    ?fields=id,access_token,instagram_business_account{id}                   │
│    &access_token={long_lived_token}                                         │
│                                                                             │
│  Returns:                                                                   │
│  {                                                                          │
│    "data": [{                                                               │
│      "id": "958164070712594",              <- facebook_page_id              │
│      "access_token": "EAATYAxh...",        <- page_access_token             │
│      "instagram_business_account": {                                        │
│        "id": "17841480050789586"           <- instagram_user_id             │
│      }                                                                      │
│    }]                                                                       │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: Everything Saved to .instagram_tokens.json                         │
│                                                                             │
│  {                                                                          │
│    "access_token": "EAATYAxh...",           <- Main token (60 days)         │
│    "page_access_token": "EAATYAxh...",      <- For messaging API            │
│    "facebook_page_id": "958164070712594",   <- Auto-detected                │
│    "instagram_user_id": "17841480050789586",<- Auto-detected                │
│    "expires_in": 5184000,                   <- 60 days in seconds           │
│    "access_token_saved_at": 1769688710      <- Timestamp when saved         │
│  }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Understanding the Tokens & IDs

| Token/ID | What It Is | Used For | How It's Obtained |
|----------|-----------|----------|-------------------|
| `access_token` | User Access Token (60 days) | All API calls except messaging | OAuth flow -> fb_exchange_token |
| `page_access_token` | Page Access Token | Messaging/DM API ONLY | GET /me/accounts |
| `instagram_user_id` | Your Instagram account ID | API endpoints like `{id}/media` | From /me/accounts response |
| `facebook_page_id` | Your Facebook Page ID | Conversations API endpoint | From /me/accounts response |
| `expires_in` | Token lifetime (seconds) | Auto-refresh calculation | From API response |

### How Each Tool Uses Tokens

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TOOL EXECUTION FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. LOAD TOKENS from .instagram_tokens.json                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. CHECK EXPIRY                                                            │
│     - If token expires within 1 day -> AUTO-REFRESH                         │
│     - New 60-day token obtained and saved                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. AUTO-DETECT instagram_user_id if needed                                 │
│     - Calls /me/accounts to get Instagram Business Account ID               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. SELECT CORRECT TOKEN                                                    │
│                                                                             │
│     ┌──────────────────────┬──────────────────────────┐                     │
│     │ Tool Type            │ Token Used               │                     │
│     ├──────────────────────┼──────────────────────────┤                     │
│     │ Publishing           │ access_token             │                     │
│     │ Media                │ access_token             │                     │
│     │ Comments             │ access_token             │                     │
│     │ Insights             │ access_token             │                     │
│     │ User Info            │ access_token             │                     │
│     │ MESSAGING (DMs)      │ page_access_token        │                     │
│     └──────────────────────┴──────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. MAKE API CALL                                                           │
│     GET https://graph.facebook.com/v21.0/{endpoint}                         │
│       ?access_token={selected_token}                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Token Refresh System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TOKEN LIFECYCLE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Day 0     Day 30    Day 59        Day 60                                   │
│    │         │         │             │                                      │
│    │◄────────│─────────│─────────────┤                                      │
│    │         │         │   ▲         │                                      │
│    │  Token Valid      │   │         │                                      │
│    │                   │   │         │                                      │
│    │              ┌────┴───┴────┐    │                                      │
│    │              │ AUTO-REFRESH│    │                                      │
│    │              │ TRIGGERED   │    │                                      │
│    │              │ (1 day      │    │                                      │
│    │              │  before     │    │                                      │
│    │              │  expiry)    │    │                                      │
│    │              └─────────────┘    │                                      │
│                                                                             │
│  Key: Refresh happens automatically when you make any API call              │
│       on Day 59 or later. New 60-day token is saved.                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Important:** Facebook doesn't use separate refresh tokens. The access_token itself acts as the refresh token when using the `fb_exchange_token` grant type.

---

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

---

## How to Get IDs for API Calls

### Getting `ig_media_id` (for insights, comments)

```
Step 1: Call GET_USER_MEDIA
        └── Returns array of posts

Step 2: Each post has an "id" field
        └── This is your ig_media_id

Example Response:
{
  "data": [
    {
      "id": "18067081835228178",  <-- Use this as ig_media_id
      "caption": "My post",
      "media_type": "IMAGE"
    }
  ]
}
```

### Getting `conversation_id` (for messaging)

```
Step 1: Call LIST_ALL_CONVERSATIONS
        └── Returns array of conversations

Step 2: Each conversation has an "id" field
        └── This is your conversation_id

Example Response:
{
  "data": [
    {
      "id": "aWdfc...",           <-- Use this as conversation_id
      "participants": [
        {"id": "17841400000000000"}  <-- recipient_id for sending
      ]
    }
  ]
}
```

### Getting `recipient_id` (for DMs)

**Option 1: From conversations**
```
LIST_ALL_CONVERSATIONS
  └── data[].participants[].id = recipient_id
```

**Option 2: From username lookup**
```
GET_USER_BY_USERNAME(username="someuser")
  └── Returns: { "instagram_user_id": "17841400000000000" }
  └── Use instagram_user_id as recipient_id
```

### Getting `creation_id` (for publishing)

```
Step 1: CREATE_MEDIA_CONTAINER
        └── Returns: { "id": "17889455560051444" }

Step 2: Use this "id" as creation_id in:
        - GET_POST_STATUS
        - CREATE_POST
        - POST_IG_USER_MEDIA_PUBLISH
```

---

## Usage Examples

### Create and Publish a Photo

```
// Step 1: Create container
CREATE_MEDIA_CONTAINER
  image_url: "https://example.com/photo.jpg"
  caption: "Hello Instagram! #mcp"

// Response: { "id": "17889455560051444" }

// Step 2: Check status (optional for images)
GET_POST_STATUS
  creation_id: "17889455560051444"

// Response: { "status_code": "FINISHED" }

// Step 3: Publish
CREATE_POST
  creation_id: "17889455560051444"

// Response: { "id": "18067081835228178" }  <-- Published post ID
```

### Get Post Insights

```
// Step 1: Get your posts
GET_USER_MEDIA
  limit: 10

// Step 2: Use post ID for insights
GET_IG_MEDIA_INSIGHTS
  ig_media_id: "18067081835228178"
  metric: ["reach", "likes", "comments", "saved"]
```

### Send a DM

```
// Step 1: Get conversations to find recipient
LIST_ALL_CONVERSATIONS

// Step 2: Send message
SEND_TEXT_MESSAGE
  recipient_id: "17841400000000000"
  text: "Hello from MCP!"
```

---

## Configuration

### Required .env Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OAUTH2_CLIENT_ID` | Yes | Facebook App ID |
| `OAUTH2_CLIENT_SECRET` | Yes | Facebook App Secret |
| `OAUTH2_REDIRECT_URI` | No | Default: `http://localhost:8080/callback` |

### Auto-Detected (No Setup Needed)

| Variable | Description |
|----------|-------------|
| `INSTAGRAM_USER_ID` | Auto-detected from token |
| `FACEBOOK_PAGE_ID` | Auto-detected from token |
| `INSTAGRAM_PAGE_ACCESS_TOKEN` | Auto-detected from token |
| `INSTAGRAM_GRAPH_API_VERSION` | Default: `v21.0` |

### Token Storage (.instagram_tokens.json)

```json
{
  "access_token": "EAATYAxh...",
  "page_access_token": "EAATYAxh...",
  "facebook_page_id": "958164070712594",
  "instagram_user_id": "17841480050789586",
  "expires_in": 5184000,
  "access_token_saved_at": 1769688710
}
```

---

## Messaging Limitations

⚠️ **24-Hour Window Policy:**
- Recipients must message you FIRST before you can reply
- Use `LIST_ALL_CONVERSATIONS` to find active conversations
- App Review required to initiate conversations

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Invalid OAuth access token` | Token expired or invalid | Run `oauth_setup.py` again |
| `Media not ready` | Container still processing | Wait a few seconds, use `GET_POST_STATUS` |
| `Rate limit exceeded` | Too many posts | Max 25 posts per 24 hours |
| `Personal account not supported` | Wrong account type | Switch to Business/Creator account |
| `Page not found` | No Facebook Page | Connect Instagram to a Facebook Page |
| `Error (#3) Capability` | 24-hour window | Recipient must message you first |
| `Error (#190) Page Access Token` | Missing page token | Run `get_page_token.py` |
| `metric[x] must be one of...` | Invalid metric name | Check valid metrics for endpoint |
| `impressions not supported` | API v22.0+ change | Use `reach` instead of `impressions` |

---

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

---

## Requirements

- Python 3.10+
- Instagram Business or Creator account
- Facebook App with Instagram permissions
- Account connected to a Facebook Page

---

## License

MIT License
