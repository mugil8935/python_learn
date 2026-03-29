"""
HTTP Server wrapper for MCP Test Server
Run this on the remote machine to expose the server over HTTP
"""

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from mcp_test_server.server import MCPTestServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_instance = MCPTestServer()


class MCPHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for MCP requests"""
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            request = json.loads(body)
            
            if self.path == "/tools/list":
                response = server_instance.get_tools()
            elif self.path == "/tools/call":
                tool_name = request.get("name")
                arguments = request.get("arguments", {})
                response = server_instance.call_tool(tool_name, **arguments)
            else:
                response = {"error": "Unknown endpoint"}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Log requests"""
        logger.info(format % args)


def run_server(host='0.0.0.0', port=8000):
    """Run the HTTP server"""
    server = HTTPServer((host, port), MCPHTTPHandler)
    logger.info(f"MCP HTTP Server running on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        server.server_close()


if __name__ == "__main__":
    run_server()
