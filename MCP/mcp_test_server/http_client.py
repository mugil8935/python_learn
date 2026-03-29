"""
HTTP Client for connecting Claude Desktop to remote MCP Server
This acts as a bridge between Claude and the HTTP server
"""

import json
import subprocess
import sys
import requests
from typing import Any, Dict, Optional


class RemoteMCPClient:
    """Client to connect to remote MCP server via HTTP"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        """
        Initialize remote MCP client
        
        Args:
            server_url: URL of the remote HTTP MCP server
        """
        self.server_url = server_url
        self.tools_cache: Optional[list] = None
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make HTTP request to remote server"""
        url = f"{self.server_url}{endpoint}"
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                response = requests.get(url, timeout=10)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to connect to {url}: {str(e)}")
    
    def get_tools(self) -> list:
        """Get list of available tools from remote server"""
        if self.tools_cache is None:
            self.tools_cache = self._make_request("/tools/list")
        return self.tools_cache
    
    def call_tool(self, tool_name: str, **arguments) -> Any:
        """Call a tool on the remote server"""
        result = self._make_request(
            "/tools/call",
            method="POST",
            data={
                "name": tool_name,
                "arguments": arguments
            }
        )
        return result


def handle_stdio_request(request: Dict, remote_url: str) -> Dict:
    """
    Handle JSON-RPC requests from Claude and forward to remote server
    This allows Claude to communicate with remote MCP server via stdio
    """
    client = RemoteMCPClient(remote_url)
    
    try:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "Remote MCP Test Server",
                    "version": "0.1.0"
                }
            }
        elif method == "tools/list":
            result = client.get_tools()
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            result = client.call_tool(tool_name, **tool_args)
        else:
            return {
                "id": request_id,
                "error": {"code": -32601, "message": "Method not found"},
                "jsonrpc": "2.0"
            }
        
        return {
            "id": request_id,
            "result": result,
            "jsonrpc": "2.0"
        }
    except Exception as e:
        return {
            "id": request.get("id"),
            "error": {"code": -32000, "message": str(e)},
            "jsonrpc": "2.0"
        }


def stdio_bridge(remote_url: str = "http://localhost:8000"):
    """
    Bridge between Claude (stdin/stdout) and remote MCP server (HTTP)
    This reads JSON-RPC requests from stdin and forwards to remote server
    """
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line)
            response = handle_stdio_request(request, remote_url)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            error_response = {
                "error": {"code": -32700, "message": "Parse error"},
                "jsonrpc": "2.0"
            }
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            error_response = {
                "error": {"code": -32000, "message": str(e)},
                "jsonrpc": "2.0"
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="HTTP bridge for remote MCP server")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Remote MCP server URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    stdio_bridge(args.url)
