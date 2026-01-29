"""
Instagram MCP Configuration

Settings loaded from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Configuration settings for Instagram MCP."""
    
    # Instagram API
    graph_api_version: str = "v21.0"
    
    # OAuth2 Configuration
    oauth2_client_id: Optional[str] = None
    oauth2_client_secret: Optional[str] = None
    oauth2_redirect_uri: str = "http://localhost:8080/callback"
    oauth2_scopes: str = "instagram_basic,instagram_content_publish,instagram_manage_comments,instagram_manage_insights,pages_show_list,pages_read_engagement,pages_messaging,instagram_manage_messages"
    
    # Optional Backend Integration
    backend_api_url: Optional[str] = None
    backend_api_key: Optional[str] = None
    mcp_identifier: str = "instagram-mcp"
    agent_id: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls(
            graph_api_version=os.getenv("INSTAGRAM_GRAPH_API_VERSION", "v21.0"),
            oauth2_client_id=os.getenv("OAUTH2_CLIENT_ID"),
            oauth2_client_secret=os.getenv("OAUTH2_CLIENT_SECRET"),
            oauth2_redirect_uri=os.getenv("OAUTH2_REDIRECT_URI", "http://localhost:8080/callback"),
            oauth2_scopes=os.getenv("OAUTH2_SCOPES", "instagram_basic,instagram_content_publish,instagram_manage_comments,instagram_manage_insights,pages_show_list,pages_read_engagement,pages_messaging,instagram_manage_messages"),
            backend_api_url=os.getenv("BACKEND_API_URL"),
            backend_api_key=os.getenv("BACKEND_API_KEY"),
            mcp_identifier=os.getenv("MCP_IDENTIFIER", "instagram-mcp"),
            agent_id=os.getenv("AGENT_ID"),
        )


# Singleton settings instance
settings = Settings.from_env()

