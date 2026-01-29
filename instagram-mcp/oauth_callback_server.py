#!/usr/bin/env python3
"""
Simple OAuth2 callback server for Instagram authentication.
This server listens on localhost:8080 and captures the authorization code.
"""

import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import webbrowser

PORT = 8080
captured_code = None
captured_state = None

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
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Successful</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 40px; text-align: center; }}
                    .success {{ color: #2e7d32; background: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 600px; }}
                    .code {{ background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0; word-break: break-all; font-family: monospace; }}
                    .instructions {{ text-align: left; margin: 20px auto; max-width: 600px; background: #fff3e0; padding: 20px; border-radius: 8px; }}
                </style>
            </head>
            <body>
                <h1>✅ Authorization Successful!</h1>
                <div class="success">
                    <p>Your authorization code has been captured.</p>
                </div>
                <div class="code">
                    <strong>Authorization Code:</strong><br>
                    {captured_code}
                </div>
                <div class="instructions">
                    <h3>Next Steps:</h3>
                    <ol>
                        <li>Copy the authorization code above</li>
                        <li>Use the <code>OAUTH2_EXCHANGE_CODE</code> tool with this code</li>
                        <li>Or run: <code>python -c "from instagram_mcp_server import _exchange_oauth2_code; print(_exchange_oauth2_code('{captured_code}'))"</code></li>
                    </ol>
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
            print(f"\n{'='*60}")
            print("Next steps:")
            print("1. Use OAUTH2_EXCHANGE_CODE tool with this code")
            print("2. Or the code is stored in the server variable")
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
                <p>If you see this message, make sure you're using the correct redirect URI.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def run_callback_server():
    """Start the OAuth callback server."""
    global captured_code
    
    with socketserver.TCPServer(("", PORT), OAuthCallbackHandler) as httpd:
        print(f"\n{'='*60}")
        print("OAuth2 Callback Server Started")
        print(f"{'='*60}")
        print(f"Listening on: http://localhost:{PORT}/callback")
        print(f"\nThe server will automatically capture the authorization code.")
        print(f"Press Ctrl+C to stop the server after authorization.\n")
        print(f"{'='*60}\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
            if captured_code:
                return captured_code
            return None

if __name__ == "__main__":
    print("Starting OAuth2 callback server...")
    code = run_callback_server()
    if code:
        print(f"\nCaptured code: {code}")
    else:
        print("\nNo code captured. Make sure you completed the authorization flow.")






