"""
MCP Server Implementation
Provides tools and resources via JSON-RPC over stdio
"""

import json
import sys
from typing import Any, Dict, List, Optional


class MCPServer:
    """Basic MCP Server implementation"""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.resources: Dict[str, str] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools"""
        self.register_tool(
            "add",
            "Add two numbers",
            {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            self._tool_add
        )
        self.register_tool(
            "multiply",
            "Multiply two numbers",
            {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            self._tool_multiply
        )
        self.register_tool(
            "get_info",
            "Get server information",
            {},
            self._tool_get_info
        )
    
    def register_tool(self, name: str, description: str, input_schema: Dict, handler):
        """Register a tool with the server"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": input_schema,
                "required": list(input_schema.keys())
            },
            "handler": handler
        }
    
    def _tool_add(self, a: float, b: float) -> float:
        """Add two numbers"""
        return a + b
    
    def _tool_multiply(self, a: float, b: float) -> float:
        """Multiply two numbers"""
        return a * b
    
    def _tool_get_info(self) -> Dict[str, str]:
        """Get server information"""
        return {
            "name": "MCP Test Server",
            "version": "1.0.0",
            "tools_available": len(self.tools)
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "tools/list":
                result = self._list_tools()
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = self._call_tool(tool_name, tool_args)
            elif method == "initialize":
                result = self._initialize()
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
    
    def _initialize(self) -> Dict[str, Any]:
        """Initialize server"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "MCP Test Server",
                "version": "1.0.0"
            }
        }
    
    def _list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        tools_list = []
        for tool_name, tool_info in self.tools.items():
            tools_list.append({
                "name": tool_info["name"],
                "description": tool_info["description"],
                "inputSchema": tool_info["inputSchema"]
            })
        return tools_list
    
    def _call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Call a tool with arguments"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool = self.tools[tool_name]
        handler = tool["handler"]
        return handler(**arguments)
    
    def run(self):
        """Run the server, reading JSON-RPC requests from stdin"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line)
                response = self.handle_request(request)
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
    server = MCPServer()
    server.run()
