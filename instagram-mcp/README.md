Instagram MCP Server
====================

FastMCP server exposing comprehensive Instagram tools via Instagram Graph API. Provides direct access to posting, commenting, messaging, and analytics for Instagram Business and Creator accounts.

Quick Start
-----------
1) Install dependencies

Using pip:
```
pip install -r instagram-mcp/requirements.txt
```

using uv:
```
uv pip install -r instagram-mcp/requirements.txt
```

2) Configure `.env` in `instagram-mcp/`

**Option A: Direct Access Token (Simple)**
```
INSTAGRAM_ACCESS_TOKEN=your_access_token
INSTAGRAM_USER_ID=your_instagram_user_id
FACEBOOK_PAGE_ID=your_facebook_page_id  # Optional but recommended for messaging
INSTAGRAM_GRAPH_API_VERSION=v21.0  # Optional, defaults to v21.0
```

**Option B: OAuth2 Authentication (Recommended for Production)**
```
# OAuth2 Configuration
OAUTH2_CLIENT_ID=your_client_id
OAUTH2_CLIENT_SECRET=your_client_secret
OAUTH2_REDIRECT_URI=http://localhost:8080/callback  # For localhost development
# OR use: https://backend.composio.dev/api/v1/auth-apps/add  # For Composio backend
OAUTH2_SCOPES=email,manage_fundraisers,publish_video,catalog_management,pages_show_list,ads_management,ads_read,business_management,pages_messaging,instagram_basic,instagram_manage_comments,instagram_manage_insights,instagram_content_publish,leads_retrieval,whatsapp_business_management,instagram_manage_messages,pages_read_engagement,pages_manage_metadata,pages_manage_ads,whatsapp_business_messaging,instagram_shopping_tag_products,instagram_branded_content_brand,instagram_branded_content_creator,instagram_branded_content_ads_brand,instagram_manage_upcoming_events,instagram_creator_marketplace_discovery,instagram_manage_contents  # Optional, uses defaults if not set

# After OAuth2 flow, these will be set automatically:
# INSTAGRAM_OAUTH_ACCESS_TOKEN=...
# INSTAGRAM_OAUTH_REFRESH_TOKEN=...

# Still required:
INSTAGRAM_USER_ID=your_instagram_user_id
FACEBOOK_PAGE_ID=your_facebook_page_id  # Optional but recommended for messaging
INSTAGRAM_GRAPH_API_VERSION=v21.0  # Optional, defaults to v21.0
```

**For localhost OAuth2 setup (Automated - Recommended):**
1. Add to Facebook App Settings → Valid OAuth Redirect URIs: `http://localhost:8080/callback`
2. Add to Facebook App Settings → App Domains: `localhost`
3. Run the automated setup script:
   ```bash
   uv run instagram-mcp/oauth_setup.py
   ```
   Or using Python directly:
   ```bash
   python instagram-mcp/oauth_setup.py
   ```
   This script will:
   - Generate the authorization URL
   - Open your browser automatically
   - Capture the authorization code
   - Exchange it for tokens
   - Save tokens automatically to `.instagram_tokens.json`
   - Tokens will auto-refresh when they expire

**For localhost OAuth2 setup (Manual - Legacy):**
1. Add to Facebook App Settings → Valid OAuth Redirect URIs: `http://localhost:8080/callback`
2. Add to Facebook App Settings → App Domains: `localhost`
3. Run the callback server: `python instagram-mcp/oauth_callback_server.py`
4. Manually generate the authorization URL and visit it in your browser
5. The callback server will capture the authorization code

3) Run the server

Using `uv` (recommended):
```bash
uv run instagram-mcp/instagram_mcp_server.py
```

Or using Python directly:
```bash
python instagram-mcp/instagram_mcp_server.py
```

**Note**: The MCP server is configured to use `uv` by default in `mcp-config-uv.json`. The config file uses:
- Command: `uv`
- Arguments: `["run", "instagram-mcp/instagram_mcp_server.py"]`

Getting Required Credentials
-----------------------------

### INSTAGRAM_ACCESS_TOKEN

Your Instagram access token is required to use the Instagram Graph API:

1. **Create a Facebook App**:
   - Go to [Facebook Developers](https://developers.facebook.com/)
   - Create a new app or use an existing one
   - Add "Instagram" product to your app

2. **Get Access Token**:
   - Use [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
   - Select your app
   - Generate a User Access Token with required permissions:
     - `instagram_basic`
     - `instagram_content_publish`
     - `instagram_manage_comments`
     - `instagram_manage_messages`
     - `pages_read_engagement`
     - `pages_manage_posts`
   
3. **Exchange for Long-Lived Token** (recommended for production):
   - Short-lived tokens expire in 1 hour
   - Long-lived tokens last 60 days
   - Use the `/oauth/access_token` endpoint to exchange

### INSTAGRAM_USER_ID

Your Instagram Business or Creator account ID:

1. **Get from Graph API Explorer**:
   - Use the explorer with your access token
   - Query: `me/accounts` to get your Facebook Pages
   - Query: `{page-id}?fields=instagram_business_account` to get Instagram account
   - The `id` field is your Instagram User ID

2. **Important Notes**:
   - Only Instagram Business and Creator accounts are supported
   - Personal Instagram accounts are NOT supported
   - Your Instagram account must be connected to a Facebook Page

Configuration
-------------

### Authentication Methods

You can authenticate using either:
1. **Direct Access Token** (simple, for development)
2. **OAuth2** (recommended for production, supports token refresh)

### Required Variables

**For Direct Access Token:**
- `INSTAGRAM_ACCESS_TOKEN`: Your Instagram Graph API access token (Page Access Token recommended for messaging)
- `INSTAGRAM_USER_ID`: Your Instagram Business/Creator account ID

**For OAuth2:**
- `OAUTH2_CLIENT_ID`: Your OAuth2 client ID (required)
- `OAUTH2_CLIENT_SECRET`: Your OAuth2 client secret (required)
- `INSTAGRAM_USER_ID`: Your Instagram Business/Creator account ID
- **Token Storage**: Tokens are automatically saved to `.instagram_tokens.json` and will auto-refresh when expired

### Optional Variables

- `FACEBOOK_PAGE_ID`: Your Facebook Page ID (auto-detected if not provided, but recommended for messaging features)
- `INSTAGRAM_GRAPH_API_VERSION`: Graph API version (default: v21.0)
- `OAUTH2_REDIRECT_URI`: OAuth2 redirect URI (defaults to `http://localhost:8080/callback` for automated setup)
- `OAUTH2_SCOPES`: OAuth2 scopes (defaults to comprehensive set including: email, manage_fundraisers, publish_video, catalog_management, pages_show_list, ads_management, ads_read, business_management, pages_messaging, instagram_basic, instagram_manage_comments, instagram_manage_insights, instagram_content_publish, leads_retrieval, whatsapp_business_management, instagram_manage_messages, pages_read_engagement, pages_manage_metadata, pages_manage_ads, whatsapp_business_messaging, instagram_shopping_tag_products, instagram_branded_content_brand, instagram_branded_content_creator, instagram_branded_content_ads_brand, instagram_manage_upcoming_events, instagram_creator_marketplace_discovery, instagram_manage_contents)

These can be set in a `.env` file in the `instagram-mcp/` directory or as system environment variables.

### OAuth2 Setup

**Automated Setup (Recommended):**
Run the automated setup script:
```bash
uv run instagram-mcp/oauth_setup.py
```
Or using Python directly:
```bash
python instagram-mcp/oauth_setup.py
```

This will handle the complete OAuth flow automatically:
1. Generate authorization URL
2. Open browser for authorization
3. Capture authorization code
4. Exchange code for tokens
5. Save tokens to `.instagram_tokens.json` (automatically excluded from git)
6. Tokens will auto-refresh when they expire

Tools
-----

### Posting
- INSTAGRAM_CREATE_MEDIA_CONTAINER: Create a draft media container for photos/videos/reels
- INSTAGRAM_CREATE_CAROUSEL_CONTAINER: Create a draft carousel post with multiple images/videos
- INSTAGRAM_CREATE_POST: Publish a draft media container to Instagram
- INSTAGRAM_GET_POST_STATUS: Check the status of a media container

### Comments
- INSTAGRAM_GET_MEDIA_COMMENTS: Retrieve comments on an Instagram media object
- INSTAGRAM_POST_IG_MEDIA_COMMENTS: Create a comment on an Instagram media object
- INSTAGRAM_POST_IG_COMMENT_REPLIES: Create a reply to an Instagram comment
- INSTAGRAM_DELETE_COMMENT: Delete a comment on Instagram media

### Direct Messages
- INSTAGRAM_LIST_ALL_CONVERSATIONS: List all Instagram DM conversations for the authenticated user
- INSTAGRAM_GET_CONVERSATION: Retrieve a conversation with a specific user via Instagram DM
- INSTAGRAM_LIST_ALL_MESSAGES: List all messages from a specific Instagram DM conversation
- INSTAGRAM_SEND_TEXT_MESSAGE: Send a text message to an Instagram user via DM
- INSTAGRAM_SEND_IMAGE: Send an image via Instagram DM to a specific user
- INSTAGRAM_MARK_SEEN: Mark Instagram DM messages as read/seen

**Important Messaging Limitations:**
- Instagram requires the **recipient must message you FIRST** before you can reply (24-hour messaging window)
- Error (#3) "Application does not have the capability" means the recipient hasn't messaged you yet
- To initiate conversations without the 24-hour window, your app needs **App Review** approval for Instagram Messaging
- Use `INSTAGRAM_LIST_ALL_CONVERSATIONS` to see who has messaged you and get valid recipient IDs

### Analytics & Media
- INSTAGRAM_GET_USER_MEDIA: Retrieve media objects for an Instagram Business or Creator account
- INSTAGRAM_GET_MEDIA_INSIGHTS: Retrieve insights/analytics for an Instagram media object

Usage Examples
-------------

OAuth2 Authentication
```
# Use the automated setup script (recommended):
uv run instagram-mcp/oauth_setup.py

# This will handle the complete OAuth flow automatically:
# - Generate authorization URL
# - Open browser for authorization
# - Capture authorization code
# - Exchange for tokens
# - Save tokens automatically
```

Create and publish a photo post
```
INSTAGRAM_CREATE_MEDIA_CONTAINER
{
  "ig_user_id": "your_instagram_user_id",
  "image_url": "https://example.com/image.jpg",
  "caption": "Check out this amazing photo! #photography",
  "media_type": "IMAGE"
}

# Get the creation_id from the response, then:
INSTAGRAM_CREATE_POST
{
  "creation_id": "creation_id_from_previous_step",
  "ig_user_id": "your_instagram_user_id"
}
```

Create a carousel post
```
# First create individual media containers for each image
# Then create carousel:
INSTAGRAM_CREATE_CAROUSEL_CONTAINER
{
  "ig_user_id": "your_instagram_user_id",
  "children": ["container_id_1", "container_id_2", "container_id_3"],
  "caption": "My carousel post! #carousel"
}
```

Get user media
```
INSTAGRAM_GET_USER_MEDIA
{
  "ig_user_id": "your_instagram_user_id",
  "limit": 10
}
```

Post a comment
```
INSTAGRAM_POST_IG_MEDIA_COMMENTS
{
  "ig_media_id": "media_id",
  "message": "Great post! 👍"
}
```

Send a DM
```
INSTAGRAM_SEND_TEXT_MESSAGE
{
  "recipient_id": "recipient_instagram_user_id",
  "text": "Hello! How are you?"
}
```

Get media insights
```
INSTAGRAM_GET_MEDIA_INSIGHTS
{
  "ig_media_id": "media_id"
}
```

Troubleshooting
---------------

### Common Errors

- **Authentication errors**: Verify your `INSTAGRAM_ACCESS_TOKEN` is valid and not expired
- **"Invalid OAuth access token"**: Token may have expired - generate a new one
- **"Media not ready"**: Wait a few seconds after creating a media container before publishing
- **"Rate limit exceeded"**: Instagram limits API-published posts to 25 per 24-hour window
- **"Personal account not supported"**: Ensure your Instagram account is a Business or Creator account
- **"Page not found"**: Ensure your Instagram account is connected to a Facebook Page

### Messaging API Errors

- **Error (#3) "Application does not have the capability"**: 
  - This is NOT a permissions issue - it's Instagram's 24-hour messaging window policy
  - The recipient MUST message you FIRST before you can reply
  - Use `INSTAGRAM_LIST_ALL_CONVERSATIONS` to see active conversations
  - To initiate conversations without this limitation, submit your app for App Review

- **Error (#100) "No matching user found"**:
  - The recipient hasn't messaged you first (24-hour window expired or never initiated)
  - Verify the recipient ID is correct
  - Ensure the recipient is a Business/Creator account

- **Error (#230) "Requires pages_messaging permission"**:
  - Your access token needs `pages_messaging` permission
  - Generate a new User Access Token with this permission from Graph API Explorer
  - Then get the Page Access Token from `me/accounts?fields=id,access_token,instagram_business_account`
- **"Invalid media type"**: Use valid media types: IMAGE, VIDEO, REELS, CAROUSEL
- **Comment restrictions**: Comments must be ≤300 chars, ≤4 hashtags, ≤1 URL, and not all caps
- **"Page not found"**: Ensure your Instagram account is connected to a Facebook Page

Security Notes
--------------
- Keep your access token secure and never share it
- Use environment variables or secure configuration management
- Consider using long-lived tokens for production (60 days vs 1 hour)
- Rotate tokens regularly for security
- Instagram Business/Creator accounts are required - personal accounts won't work

Project Layout
--------------
- `instagram-mcp/instagram_mcp_server.py`: FastMCP server and tools
- `instagram-mcp/requirements.txt`: Python dependencies
- `instagram-mcp/.env`: Environment variables (you create this)
- `instagram-mcp/README.md`: This documentation

API Reference
-------------
This MCP server provides direct access to Instagram Graph API:
- **Posting**: Create and publish photos, videos, reels, and carousels
- **Comments**: Get, post, reply to, and delete comments
- **Direct Messages**: Send text messages and images
- **Analytics**: Get media insights and user media lists

All tools return standardized responses with `data`, `error`, and `successful` fields.

Error Handling
--------------
All tools include comprehensive error handling:
- Input validation for required parameters
- API error translation
- Network error handling
- Authentication error handling

The server will return detailed error messages to help with debugging.

Development
-----------
To extend the server:

1. Add new tools using the `@mcp.tool` decorator
2. Follow the existing pattern for parameter validation
3. Use the `make_api_request()` helper function
4. Return standardized response format with `data`, `error`, and `successful` fields

Example new tool:
```python
@mcp.tool(
    "INSTAGRAM_CUSTOM_TOOL",
    description="Custom tool description.",
)
def INSTAGRAM_CUSTOM_TOOL(
    param: Annotated[str, "Parameter description."]
):
    try:
        result = make_api_request("GET", "endpoint", params={"param": param})
        return {"data": result, "error": "", "successful": True}
    except Exception as e:
        return {"data": {}, "error": f"Failed: {str(e)}", "successful": False}
```

License
-------
This project is licensed under the MIT license.

