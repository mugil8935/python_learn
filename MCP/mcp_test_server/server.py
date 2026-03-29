"""
MCP Test Server Implementation
Implements the Model Context Protocol for providing tools to Claude
"""

import logging
from typing import Any, Dict, Optional

try:
    from mcp.server import Server
    from mcp.types import (
        Tool,
        TextContent,
        ToolResult,
    )
except ImportError:
    # Fallback for when MCP SDK is not available
    Server = object
    Tool = dict
    TextContent = dict
    ToolResult = dict

logger = logging.getLogger(__name__)


class MCPTestServer:
    """Test MCP Server with basic tools"""
    
    def __init__(self, name: str = "MCP Test Server", version: str = "0.1.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, callable] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools"""
        self.tools["add"] = {
            "description": "Add two numbers",
            "handler": self._tool_add,
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        }
        
        self.tools["multiply"] = {
            "description": "Multiply two numbers",
            "handler": self._tool_multiply,
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        }
        
        self.tools["get_server_info"] = {
            "description": "Get server information",
            "handler": self._tool_get_info,
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    
    def _tool_add(self, a: float, b: float) -> str:
        """Add two numbers"""
        result = a + b
        return f"The sum of {a} and {b} is {result}"
    
    def _tool_multiply(self, a: float, b: float) -> str:
        """Multiply two numbers"""
        result = a * b
        return f"The product of {a} and {b} is {result}"
    
    def _tool_get_info(self) -> str:
        """Get server information"""
        return f"Server: {self.name} v{self.version}, Tools available: {len(self.tools)}"
    
    def get_tools(self) -> list:
        """Get list of available tools for MCP"""
        tools_list = []
        for tool_name, tool_info in self.tools.items():
            tools_list.append({
                "name": tool_name,
                "description": tool_info["description"],
                "inputSchema": tool_info["input_schema"]
            })
        return tools_list
    
    def call_tool(self, tool_name: str, **arguments) -> str:
        """Call a tool by name with arguments"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"
        
        try:
            handler = self.tools[tool_name]["handler"]
            result = handler(**arguments)
            return result
        except Exception as e:
            return f"Error calling {tool_name}: {str(e)}"


async def main():
    """Entry point for running the server"""
    # This would be implemented with the official MCP SDK
    # For now, this is a placeholder for the async server implementation
    pass


if __name__ == "__main__":
    server = MCPTestServer()
    print(f"Starting {server.name}...")
    print(f"Available tools: {[t['name'] for t in server.get_tools()]}")
