"""
MCP Client Implementation
Connects to MCP server and communicates via JSON-RPC
"""

import json
import subprocess
import sys
from typing import Any, Dict, List, Optional


class MCPClient:
    """MCP Client for communicating with MCP servers"""
    
    def __init__(self, server_command: str = None):
        """
        Initialize MCP client
        
        Args:
            server_command: Command to start the server (e.g., "python mcp_server.py")
        """
        self.server_command = server_command
        self.process = None
        self.request_id = 0
        self.available_tools: List[Dict] = []
    
    def connect(self):
        """Connect to the MCP server"""
        if self.server_command:
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        else:
            raise RuntimeError("No server command provided")
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.process:
            self.process.stdin.close()
            self.process.wait()
            self.process = None
    
    def _send_request(self, method: str, params: Dict = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server"""
        if not self.process:
            raise RuntimeError("Not connected to server")
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        # Send request
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        
        # Read response
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("Server closed connection")
        
        response = json.loads(response_line)
        
        # Check for errors
        if "error" in response:
            raise RuntimeError(f"Server error: {response['error']['message']}")
        
        return response.get("result")
    
    def initialize(self) -> Dict[str, Any]:
        """Initialize the client connection"""
        return self._send_request("initialize")
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        self.available_tools = self._send_request("tools/list")
        return self.available_tools
    
    def call_tool(self, tool_name: str, **arguments) -> Any:
        """
        Call a tool on the server
        
        Args:
            tool_name: Name of the tool to call
            **arguments: Arguments to pass to the tool
            
        Returns:
            Result from the tool
        """
        result = self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments
            }
        )
        return result
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool"""
        for tool in self.available_tools:
            if tool["name"] == tool_name:
                return tool
        return None


def _get_demo_value(param_type: str, index: int) -> Any:
    """Generate a demo value based on MCP input schema type"""
    if param_type in ("number", "integer"):
        return index + 1
    if param_type == "boolean":
        return True
    if param_type == "array":
        return []
    if param_type == "object":
        return {}
    return f"sample-{index}"


def main():
    """Example usage of MCP client"""
    # Create client
    client = MCPClient(server_command="python mcp_server.py")
    
    try:
        # Connect to server
        print("Connecting to MCP server...")
        client.connect()
        
        # Initialize
        print("Initializing...")
        init_result = client.initialize()
        print(f"Server: {init_result['serverInfo']['name']} v{init_result['serverInfo']['version']}")
        
        # List available tools
        print("\nAvailable tools:")
        tools = client.list_tools()
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Call tools dynamically from listed schemas
        print("\nCalling tools...")
        for tool in tools:
            tool_name = tool["name"]
            input_schema = tool.get("inputSchema", {})
            properties = input_schema.get("properties", {})

            arguments: Dict[str, Any] = {}
            for index, (arg_name, arg_schema) in enumerate(properties.items(), start=1):
                arg_type = arg_schema.get("type", "string")
                arguments[arg_name] = _get_demo_value(arg_type, index)

            result = client.call_tool(tool_name, **arguments)
            if arguments:
                args_text = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
                print(f"{tool_name}({args_text}) = {result}")
            else:
                print(f"{tool_name}() = {result}")
        
        print("\nClient-server communication successful!")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
