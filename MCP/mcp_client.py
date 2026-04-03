"""
MCP Client Implementation
Connects to MCP server and communicates via JSON-RPC
"""

import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


class MCPClient:
    """MCP Client for communicating with MCP servers"""
    
    def __init__(self, server_command: Union[str, List[str]] = None):
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
            try:
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.close()
            except Exception:
                pass
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
            return_code = self.process.poll()
            if return_code is not None:
                stderr_output = ""
                if self.process.stderr:
                    stderr_output = self.process.stderr.read().strip()
                message = f"Server closed connection (exit code {return_code})"
                if stderr_output:
                    message += f": {stderr_output}"
                raise RuntimeError(message)
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


def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words"""
    return re.findall(r"[a-zA-Z_]+", text.lower())


def _select_tool_for_prompt(prompt: str, tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Choose the most relevant tool for a natural-language prompt"""
    prompt_lower = prompt.lower()
    prompt_tokens = set(_tokenize(prompt))

    best_tool = None
    best_score = 0

    for tool in tools:
        tool_name = tool.get("name", "")
        description = tool.get("description", "")
        input_schema = tool.get("inputSchema", {})
        properties = input_schema.get("properties", {})

        score = 0
        if tool_name.lower() in prompt_lower:
            score += 10

        searchable_text = " ".join(
            [
                tool_name,
                description,
                " ".join(properties.keys()),
            ]
        ).lower()
        searchable_tokens = set(_tokenize(searchable_text))
        overlap = prompt_tokens.intersection(searchable_tokens)
        score += len(overlap)

        if score > best_score:
            best_score = score
            best_tool = tool

    return best_tool if best_score > 0 else None


def _convert_user_value(raw_value: str, param_type: str) -> Any:
    """Convert user-provided string to schema-typed value"""
    text = raw_value.strip()

    if param_type == "integer":
        return int(text)
    if param_type == "number":
        return float(text)
    if param_type == "boolean":
        lowered = text.lower()
        if lowered in ("true", "1", "yes", "y", "on"):
            return True
        if lowered in ("false", "0", "no", "n", "off"):
            return False
        raise ValueError("Expected boolean value (true/false)")
    if param_type == "array":
        return json.loads(text)
    if param_type == "object":
        return json.loads(text)
    return text


def _extract_arguments_from_prompt(prompt: str, tool: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Extract likely tool arguments from natural language prompt"""
    input_schema = tool.get("inputSchema", {})
    properties: Dict[str, Dict[str, Any]] = input_schema.get("properties", {})
    required = input_schema.get("required", list(properties.keys()))

    arguments: Dict[str, Any] = {}
    numeric_values = re.findall(r"-?\d+(?:\.\d+)?", prompt)
    numeric_index = 0

    for param_name, param_schema in properties.items():
        param_type = param_schema.get("type", "string")

        if param_type in ("number", "integer") and numeric_index < len(numeric_values):
            value = numeric_values[numeric_index]
            numeric_index += 1
            arguments[param_name] = int(value) if param_type == "integer" else float(value)
            continue

        if param_type == "boolean":
            lowered = prompt.lower()
            if any(word in lowered for word in [" true", " yes", " enable", " on"]):
                arguments[param_name] = True
                continue
            if any(word in lowered for word in [" false", " no", " disable", " off"]):
                arguments[param_name] = False
                continue

        if param_type == "string":
            quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', prompt)
            if quoted:
                first_quoted = quoted[0][0] if quoted[0][0] else quoted[0][1]
                arguments[param_name] = first_quoted

    missing_required = [name for name in required if name not in arguments]
    return arguments, missing_required


def main():
    """Interactive MCP chatbot that chooses tools from user prompts"""
    server_path = os.path.join(os.path.dirname(__file__), "mcp_server.py")
    client = MCPClient(server_command=[sys.executable, server_path])
    
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

        print("\nChatbot ready. Type a prompt (or 'tools' to list, 'exit' to quit).")
        while True:
            user_prompt = input("You: ").strip()
            if not user_prompt:
                continue

            lowered = user_prompt.lower()
            if lowered in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            if lowered == "tools":
                print("Available tools:")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
                continue

            selected_tool = _select_tool_for_prompt(user_prompt, tools)
            if not selected_tool:
                print("Assistant: I could not decide which tool to use. Try mentioning the task or tool name.")
                continue

            tool_name = selected_tool["name"]
            arguments, missing_required = _extract_arguments_from_prompt(user_prompt, selected_tool)

            if missing_required:
                input_schema = selected_tool.get("inputSchema", {})
                properties = input_schema.get("properties", {})

                for arg_name in missing_required:
                    arg_schema = properties.get(arg_name, {})
                    arg_type = arg_schema.get("type", "string")
                    while True:
                        raw_value = input(f"Assistant: Enter value for {arg_name} ({arg_type}): ").strip()
                        try:
                            arguments[arg_name] = _convert_user_value(raw_value, arg_type)
                            break
                        except Exception as conversion_error:
                            print(f"Assistant: {conversion_error}")

            result = client.call_tool(tool_name, **arguments)
            print(f"Assistant: Used tool '{tool_name}' with {arguments} -> {result}")
        
        print("\nClient-server communication successful!")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
