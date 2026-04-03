"""
MCP Client Chatbot with OpenAI Tool Router
Uses OpenAI to semantically choose the best MCP tool and arguments.
"""

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from openai import OpenAI


class MCPClient:
    """MCP Client for communicating with MCP servers"""

    def __init__(self, server_command: Union[str, List[str]] = None):
        self.server_command = server_command
        self.process = None
        self.request_id = 0
        self.available_tools: List[Dict[str, Any]] = []

    def connect(self):
        """Connect to the MCP server"""
        if not self.server_command:
            raise RuntimeError("No server command provided")

        self.process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

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

    def _send_request(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Send a JSON-RPC request to the server"""
        if not self.process:
            raise RuntimeError("Not connected to server")

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }

        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

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
        if "error" in response:
            raise RuntimeError(f"Server error: {response['error']['message']}")

        return response.get("result")

    def initialize(self) -> Dict[str, Any]:
        return self._send_request("initialize")

    def list_tools(self) -> List[Dict[str, Any]]:
        self.available_tools = self._send_request("tools/list")
        return self.available_tools

    def call_tool(self, tool_name: str, **arguments) -> Any:
        return self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )


class OpenAIToolRouter:
    """Use OpenAI to map user prompts to MCP tool calls"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def route(self, user_prompt: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return routing decision with tool name and arguments"""
        tool_catalog = [
            {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {}),
            }
            for tool in tools
        ]

        system_prompt = (
            "You are a strict tool router. "
            "Choose exactly one tool from the provided list if confidence is enough, else ask for clarification. "
            "Infer arguments from user prompt using the tool input schema. "
            "Return only JSON with keys: tool_name, arguments, confidence, clarification_question."
        )

        user_payload = {
            "user_prompt": user_prompt,
            "tools": tool_catalog,
            "output_rules": {
                "tool_name": "string or null (must match exactly one tool name)",
                "arguments": "object",
                "confidence": "number between 0 and 1",
                "clarification_question": "string or empty string",
            },
        }

        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
        )

        content = completion.choices[0].message.content or "{}"
        decision = json.loads(content)

        tool_name = decision.get("tool_name")
        arguments = decision.get("arguments", {})
        confidence = decision.get("confidence", 0)
        clarification_question = decision.get("clarification_question", "")

        if not isinstance(arguments, dict):
            arguments = {}

        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "confidence": confidence,
            "clarification_question": clarification_question,
        }


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
    if param_type in ("array", "object"):
        return json.loads(text)
    return text


def _coerce_llm_arguments(tool: Dict[str, Any], raw_arguments: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Coerce LLM arguments into schema types and report missing required fields"""
    input_schema = tool.get("inputSchema", {})
    properties: Dict[str, Dict[str, Any]] = input_schema.get("properties", {})
    required = input_schema.get("required", list(properties.keys()))

    arguments: Dict[str, Any] = {}
    for arg_name, arg_schema in properties.items():
        if arg_name not in raw_arguments:
            continue
        arg_type = arg_schema.get("type", "string")
        arg_value = raw_arguments[arg_name]

        if arg_type == "integer" and not isinstance(arg_value, int):
            arguments[arg_name] = int(arg_value)
        elif arg_type == "number" and not isinstance(arg_value, (int, float)):
            arguments[arg_name] = float(arg_value)
        elif arg_type == "boolean" and not isinstance(arg_value, bool):
            if isinstance(arg_value, str):
                arguments[arg_name] = _convert_user_value(arg_value, "boolean")
            else:
                arguments[arg_name] = bool(arg_value)
        else:
            arguments[arg_name] = arg_value

    missing_required = [name for name in required if name not in arguments]
    return arguments, missing_required


def main():
    """Interactive MCP chatbot with OpenAI semantic tool routing"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        print("Set it first, for example:", file=sys.stderr)
        print("  set OPENAI_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    project_root = os.path.dirname(os.path.dirname(__file__))
    server_path = os.path.join(project_root, "mcp_server.py")
    client = MCPClient(server_command=[sys.executable, server_path])
    router = OpenAIToolRouter()

    try:
        print("Connecting to MCP server...")
        client.connect()

        print("Initializing...")
        init_result = client.initialize()
        print(f"Server: {init_result['serverInfo']['name']} v{init_result['serverInfo']['version']}")

        tools = client.list_tools()
        print("\nAvailable tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        print("\nOpenAI-routed chatbot ready. Type a prompt (or 'tools' / 'exit').")
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

            try:
                route = router.route(user_prompt, tools)
            except Exception as route_error:
                print(f"Assistant: Router error: {route_error}")
                continue

            tool_name = route.get("tool_name")
            confidence = route.get("confidence", 0)
            clarification_question = route.get("clarification_question", "")

            selected_tool = next((t for t in tools if t.get("name") == tool_name), None)
            if not selected_tool:
                if clarification_question:
                    print(f"Assistant: {clarification_question}")
                else:
                    print("Assistant: I could not confidently choose a tool. Please be more specific.")
                continue

            raw_arguments = route.get("arguments", {})
            try:
                arguments, missing_required = _coerce_llm_arguments(selected_tool, raw_arguments)
            except Exception as coerce_error:
                print(f"Assistant: Argument parse error: {coerce_error}")
                continue

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

            try:
                result = client.call_tool(tool_name, **arguments)
                print(
                    f"Assistant: Routed to '{tool_name}' (confidence={confidence}) with {arguments} -> {result}"
                )
            except Exception as tool_error:
                print(f"Assistant: Tool call failed: {tool_error}")

    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
