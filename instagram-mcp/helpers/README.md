# Instagram MCP Helper Scripts

These are standalone helper scripts that combine multiple MCP tools for common workflows.

## Available Scripts

### 1. `get_post_list.py`
Get a list of all your published Instagram posts.

**Usage:**
```bash
uv run helpers/get_post_list.py
uv run helpers/get_post_list.py --limit 50
uv run helpers/get_post_list.py --after "cursor_token"
```

**Output:** List of posts with IDs, types, captions, and timestamps.

---

### 2. `publish_post.py`
Complete workflow: Create media container and publish it.

**Usage:**
```bash
uv run helpers/publish_post.py --image_url "https://example.com/image.jpg" --caption "My post caption"
uv run helpers/publish_post.py --image_url "https://example.com/image.jpg" --caption "My post" --wait
```

**Options:**
- `--image_url`: Image URL (required)
- `--caption`: Post caption (optional)
- `--wait`: Wait for media processing before publishing (optional)
- `--ig_user_id`: Instagram user ID (optional, auto-detected)

**Output:** Published media ID that you can use for insights, comments, etc.

---

### 3. `get_post_insights.py`
Get insights/analytics for a published Instagram post.

**Usage:**
```bash
uv run helpers/get_post_insights.py --media_id "17849184327668360"
uv run helpers/get_post_insights.py --media_id "17849184327668360" --metrics reach likes comments shares
```

**Options:**
- `--media_id`: Published media ID (required) - Get from `get_post_list.py` or after publishing
- `--metrics`: Metrics to retrieve (default: reach likes comments shares saved)
- `--period`: Time period - `lifetime` or `day` (default: lifetime)

**Output:** Insights data for the specified metrics.

---

### 4. `get_post_with_insights.py`
Get list of posts with their insights in one go.

**Usage:**
```bash
uv run helpers/get_post_with_insights.py
uv run helpers/get_post_with_insights.py --limit 5 --metrics reach likes comments
```

**Options:**
- `--limit`: Number of posts (default: 10)
- `--metrics`: Insights metrics (default: reach likes comments)
- `--ig_user_id`: Instagram user ID (optional)

**Output:** List of posts with their insights data.

---

### 5. `get_conversations_with_messages.py`
Get all conversations and their recent messages.

**Usage:**
```bash
uv run helpers/get_conversations_with_messages.py
uv run helpers/get_conversations_with_messages.py --limit 5 --messages_per_conv 10
```

**Options:**
- `--limit`: Number of conversations (default: 10)
- `--messages_per_conv`: Messages per conversation (default: 5)

**Output:** List of conversations with their messages.

---

## Running the Scripts

All scripts can be run using `uv`:

```bash
uv run helpers/script_name.py [options]
```

Or with Python directly:

```bash
python helpers/script_name.py [options]
```

## Examples

**Get your posts:**
```bash
uv run helpers/get_post_list.py
```

**Publish a new post:**
```bash
uv run helpers/publish_post.py --image_url "https://picsum.photos/1080/1080" --caption "Hello Instagram!"
```

**Get insights for a post:**
```bash
uv run helpers/get_post_insights.py --media_id "17849184327668360"
```

**Get posts with insights:**
```bash
uv run helpers/get_post_with_insights.py --limit 5
```

**Get conversations:**
```bash
uv run helpers/get_conversations_with_messages.py
```




