#!/usr/bin/env python3
"""
Instagram MCP Server

A modular MCP server using dynamic tool registration from manifest.
Run with: uv run instagram-mcp/main.py
"""

import importlib
import inspect
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Force load .env from script directory
script_dir = Path(__file__).resolve().parent
env_path = script_dir / '.env'
if env_path.exists():
    load_dotenv(env_path, verbose=True)

from fastmcp import FastMCP
from fastmcp.tools.tool import FunctionTool

from config import settings
from client import InstagramClient

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger("instagram.server")

# Root path for manifest loading
ROOT_DIR = Path(__file__).resolve().parent

# Server State
state: Dict[str, Any] = {}

# Initialize MCP Server
mcp = FastMCP("instagram-mcp")


def get_client() -> InstagramClient:
    """Get or create the singleton InstagramClient."""
    if "client" not in state:
        logger.info("Initializing InstagramClient...")
        token_provider = None
        
        # Initialize Backend Client if configured (for enterprise integrations)
        if settings.backend_api_url and settings.backend_api_key:
            try:
                logger.info(f"Backend integration configured: {settings.backend_api_url}")
                # Backend client can be added here for enterprise use
            except Exception as e:
                logger.error(f"Failed to initialize backend: {e}")
        
        try:
            state["client"] = InstagramClient(settings, token_provider=token_provider)
        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            raise
    
    return state["client"]


def remove_null_from_schema(schema):
    """Remove null types from schema to prevent MCP Inspector trim() errors."""
    if isinstance(schema, dict):
        new_schema = {}
        for key, value in schema.items():
            if key == "anyOf" and isinstance(value, list):
                filtered = [v for v in value if not (isinstance(v, dict) and v.get("type") == "null")]
                if filtered:
                    if len(filtered) == 1:
                        new_schema.update(filtered[0])
                    else:
                        new_schema[key] = filtered
            elif key == "type" and isinstance(value, list) and "null" in value:
                filtered = [v for v in value if v != "null"]
                if len(filtered) == 1:
                    new_schema["type"] = filtered[0]
                else:
                    new_schema["type"] = filtered
            elif key == "type" and value == "null":
                continue
            elif key == "default" and value is None:
                continue
            else:
                new_schema[key] = remove_null_from_schema(value) if isinstance(value, (dict, list)) else value
        return new_schema
    elif isinstance(schema, list):
        return [remove_null_from_schema(item) for item in schema]
    else:
        return schema


def create_dynamic_wrapper(func, description, tool_id=None):
    """
    Creates a wrapper function that injects the client instance.
    The client provides: make_api_request, get_instagram_user_id, get_page_for_ig_account, load_tokens
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    
    # Identify which client methods this function needs
    client_params = {"make_api_request", "get_instagram_user_id", "get_page_for_ig_account", "load_tokens"}
    
    # Filter out client-injected params
    user_params = [p for p in params if p.name not in client_params]
    
    # Build param string - handle various default value types
    decl_parts = []
    names = []
    for p in user_params:
        if p.default is inspect._empty:
            decl_parts.append(p.name)
        elif p.default is None:
            decl_parts.append(f"{p.name}=None")
        elif isinstance(p.default, str):
            decl_parts.append(f"{p.name}={repr(p.default)}")
        elif isinstance(p.default, (int, float, bool)):
            decl_parts.append(f"{p.name}={p.default}")
        elif isinstance(p.default, (list, dict)):
            decl_parts.append(f"{p.name}=None")  # Handle mutable defaults safely
        else:
            decl_parts.append(f"{p.name}={repr(p.default)}")
        names.append(p.name)
    
    decl = ", ".join(decl_parts)
    
    # Build kwargs for client methods
    client_kwargs = []
    for p in params:
        if p.name == "make_api_request":
            client_kwargs.append("'make_api_request': __get_client().make_api_request")
        elif p.name == "get_instagram_user_id":
            client_kwargs.append("'get_instagram_user_id': __get_client().get_instagram_user_id")
        elif p.name == "get_page_for_ig_account":
            client_kwargs.append("'get_page_for_ig_account': __get_client().get_page_for_ig_account")
        elif p.name == "load_tokens":
            client_kwargs.append("'load_tokens': __get_client().load_tokens")
    
    client_kwargs_str = ", ".join(client_kwargs)
    user_kwargs_str = ", ".join([f"'{n}': {n}" for n in names])
    
    # Source code for wrapper
    src = (
        f"def wrapper({decl}):\n"
        f"    client_kwargs = {{{client_kwargs_str}}}\n"
        f"    user_kwargs = {{{user_kwargs_str}}}\n"
        f"    kwargs = {{**client_kwargs, **user_kwargs}}\n"
        f"    return __func(**kwargs)\n"
    )
    
    local_ns = {}
    global_ns = {
        "__func": func,
        "__get_client": get_client
    }
    
    exec(src, global_ns, local_ns)
    wrapper = local_ns["wrapper"]
    
    # Update Metadata
    wrapper.__name__ = tool_id if tool_id else func.__name__
    wrapper.__doc__ = description or func.__doc__
    
    # Update Annotations (remove client params)
    if hasattr(func, "__annotations__"):
        ann = dict(func.__annotations__)
        for cp in client_params:
            ann.pop(cp, None)
        wrapper.__annotations__ = ann
    
    return wrapper


def register_tools():
    """Register tools from tools_manifest.json dynamically."""
    manifest_path = ROOT_DIR / "tools_manifest.json"
    if not manifest_path.exists():
        logger.error(f"Manifest not found at {manifest_path}")
        return
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load manifest: {e}")
        return
    
    logger.info("Loading tools from manifest...")
    
    # Add tools directory to path
    tools_dir = ROOT_DIR / "tools"
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    
    tools_registered = 0
    for entry in manifest.get("tools", []):
        tool_id = entry.get("id")
        target = entry.get("target")
        description = entry.get("description")
        input_schema = entry.get("input_schema")
        
        if not tool_id or not target:
            continue
        
        try:
            module_name, func_name = target.split(":")
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
        except Exception as e:
            logger.error(f"Failed to import {target}: {e}")
            continue
        
        # Create Dynamic Wrapper
        try:
            wrapper = create_dynamic_wrapper(func, description, tool_id)
            
            # Use FunctionTool to create the tool object
            tool = FunctionTool.from_function(
                wrapper,
                name=tool_id,
                description=description
            )
            
            # Enforce sanitized schema from manifest
            if input_schema:
                cleaned_schema = remove_null_from_schema(input_schema)
                tool.parameters = cleaned_schema
            
            # Register with FastMCP
            mcp.add_tool(tool)
            tools_registered += 1
            logger.info(f"Registered tool: {tool_id}")
            
        except Exception as e:
            logger.error(f"Failed to wrap/register {tool_id}: {e}")
    
    logger.info(f"Total tools registered: {tools_registered}")


def main():
    """Main entry point."""
    logger.info("Starting Instagram MCP Server...")
    logger.info(f"Config: API version={settings.graph_api_version}")
    
    # Load tools
    register_tools()
    
    # Run server
    mcp.run()


if __name__ == "__main__":
    main()
