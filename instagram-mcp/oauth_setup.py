#!/usr/bin/env python3
"""
Automated OAuth2 setup script for Instagram authentication.
This script handles the complete OAuth flow automatically:
1. Generates authorization URL
2. Opens browser for user authorization
3. Captures authorization code
4. Exchanges code for tokens
5. Saves tokens automatically to persistent storage
"""

import os
import sys
import time
import webbrowser
import threading
from urllib.parse import urlparse, parse_qs
import http.server
import socketserver
from dotenv import load_dotenv

# Add the current directory to path to import from instagram_mcp_server
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Load environment variables
env_path = os.path.join(script_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Import OAuth functions from the main server
from instagram_mcp_server import (
    _is_oauth2_enabled,
    _get_oauth2_authorization_url,
    _exchange_oauth2_code,
    _get_token_storage_path
)

PORT = 8080
captured_code = None
captured_state = None
server_ready = threading.Event()

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global captured_code, captured_state
        
        # Parse the URL
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        # Check for error
        if 'error' in query_params:
            error = query_params['error'][0]
            error_reason = query_params.get('error_reason', [''])[0]
            error_description = query_params.get('error_description', [''])[0]
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 40px; text-align: center; }}
                    .error {{ color: #d32f2f; background: #ffebee; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 600px; }}
                </style>
            </head>
            <body>
                <h1>OAuth Authorization Error</h1>
                <div class="error">
                    <p><strong>Error:</strong> {error}</p>
                    <p><strong>Reason:</strong> {error_reason}</p>
                    <p><strong>Description:</strong> {error_description}</p>
                </div>
                <p>Please check your Facebook App settings and try again.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            return
        
        # Check for authorization code
        if 'code' in query_params:
            captured_code = query_params['code'][0]
            captured_state = query_params.get('state', [None])[0]
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Successful</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                    .success { color: #2e7d32; background: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 600px; }
                </style>
            </head>
            <body>
                <h1>✅ Authorization Successful!</h1>
                <div class="success">
                    <p>Your authorization code has been captured and tokens are being saved automatically.</p>
                    <p><strong>You can close this window now.</strong></p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
            print(f"\n{'='*60}")
            print("✅ Authorization code captured!")
            print(f"{'='*60}")
            print(f"Code: {captured_code}")
            if captured_state:
                print(f"State: {captured_state}")
            print(f"{'='*60}\n")
            
        else:
            # No code in URL
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth Callback</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                </style>
            </head>
            <body>
                <h1>OAuth Callback Server</h1>
                <p>Waiting for authorization code...</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def run_callback_server():
    """Start the OAuth callback server in a separate thread."""
    global captured_code
    
    def server_thread():
        with socketserver.TCPServer(("", PORT), OAuthCallbackHandler) as httpd:
            server_ready.set()
            httpd.timeout = 0.5
            while captured_code is None:
                httpd.handle_request()
    
    thread = threading.Thread(target=server_thread, daemon=True)
    thread.start()
    server_ready.wait()
    print(f"✅ Callback server started on http://localhost:{PORT}/callback")

def main():
    """Main OAuth setup flow."""
    print(f"\n{'='*60}")
    print("Instagram OAuth2 Automated Setup")
    print(f"{'='*60}\n")
    
    # Check if OAuth2 is configured
    if not _is_oauth2_enabled():
        print("❌ Error: OAuth2 is not configured.")
        print("\nPlease set the following environment variables in your .env file:")
        print("  - OAUTH2_CLIENT_ID")
        print("  - OAUTH2_CLIENT_SECRET")
        print("  - OAUTH2_REDIRECT_URI (optional, defaults to http://localhost:8080/callback)")
        print("  - OAUTH2_SCOPES (optional)")
        sys.exit(1)
    
    # Check if tokens already exist
    token_file = _get_token_storage_path()
    if os.path.exists(token_file):
        print("⚠️  Warning: Tokens already exist in storage.")
        response = input("Do you want to re-authenticate? (y/N): ").strip().lower()
        if response != 'y':
            print("Keeping existing tokens. Exiting.")
            sys.exit(0)
    
    try:
        # Step 1: Generate authorization URL
        print("Step 1: Generating authorization URL...")
        auth_url = _get_oauth2_authorization_url()
        print(f"✅ Authorization URL generated\n")
        
        # Step 2: Start callback server
        print("Step 2: Starting callback server...")
        run_callback_server()
        time.sleep(1)  # Give server a moment to start
        print()
        
        # Step 3: Open browser
        print("Step 3: Opening browser for authorization...")
        print(f"   URL: {auth_url}\n")
        webbrowser.open(auth_url)
        print("✅ Browser opened. Please authorize the application.\n")
        print("Waiting for authorization code...")
        print("(This may take a few minutes. Press Ctrl+C to cancel)\n")
        
        # Step 4: Wait for authorization code
        timeout = 300  # 5 minutes
        start_time = time.time()
        while captured_code is None:
            if time.time() - start_time > timeout:
                print("\n❌ Timeout: No authorization code received within 5 minutes.")
                sys.exit(1)
            time.sleep(0.5)
        
        # Step 5: Exchange code for tokens
        print("\nStep 4: Exchanging authorization code for tokens...")
        try:
            token_data = _exchange_oauth2_code(captured_code)
            print("✅ Tokens received and saved automatically!\n")
            
            # Display token info
            print(f"{'='*60}")
            print("✅ OAuth Setup Complete!")
            print(f"{'='*60}")
            print(f"Access Token: {token_data.get('access_token', 'N/A')[:20]}...")
            if 'expires_in' in token_data:
                print(f"Expires in: {token_data['expires_in']} seconds")
            if 'refresh_token' in token_data:
                print(f"Refresh Token: {token_data['refresh_token'][:20]}...")
            print(f"\nTokens saved to: {token_file}")
            print(f"{'='*60}\n")
            
            print("🎉 Your Instagram MCP server is now authenticated!")
            print("The tokens will be automatically refreshed when they expire.\n")
            
        except Exception as e:
            print(f"\n❌ Error exchanging code for tokens: {e}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


