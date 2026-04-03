"""
MCP Client Chatbot with OpenAI Tool Router (Multi Web Transport)
Routes prompts with OpenAI and calls MCP tools over multiple HTTP JSON-RPC servers.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests
from openai import OpenAI


class MCPWebClient:
    """MCP Client for communicating with MCP web server via HTTP JSON-RPC"""

    def __init__(
        self,
        endpoint_url: str,
        timeout_seconds: int = 30,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.headers = headers or {}
        self.request_id = 0
        self.available_tools: List[Dict[str, Any]] = []

    def connect(self):
        """Validate connectivity by sending initialize"""
        self.initialize()

    def disconnect(self):
        """No persistent connection required for HTTP transport"""
        return None

    def _send_request(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Send a JSON-RPC request to the MCP web endpoint"""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }

        try:
            response = requests.post(
                self.endpoint_url,
                json=payload,
                timeout=self.timeout_seconds,
                headers=self.headers,
            )
            response.raise_for_status()
        except Exception as error:
            raise RuntimeError(f"HTTP request failed for {self.endpoint_url}: {error}")

        try:
            response_json = response.json()
        except Exception as error:
            raise RuntimeError(f"Invalid JSON response from server {self.endpoint_url}: {error}")

        if "error" in response_json:
            error_info = response_json.get("error", {})
            raise RuntimeError(f"Server error: {error_info.get('message', 'Unknown error')}")

        return response_json.get("result")

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
            "Tool names may be namespaced like 'local:add' or 'atlassian:search_issue'. "
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

        arguments = decision.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}

        return {
            "tool_name": decision.get("tool_name"),
            "arguments": arguments,
            "confidence": decision.get("confidence", 0),
            "clarification_question": decision.get("clarification_question", ""),
        }


def _convert_user_value(raw_value: str, param_type: str) -> Any:
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


def _build_headers(api_key_env_name: str) -> Dict[str, str]:
    api_key = os.getenv(api_key_env_name, "").strip()
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


def _load_server_tools(server_name: str, client: MCPWebClient) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    init_result = client.initialize()
    raw_tools = client.list_tools()

    namespaced_tools: List[Dict[str, Any]] = []
    for tool in raw_tools:
        namespaced_tools.append(
            {
                "name": f"{server_name}:{tool['name']}",
                "description": f"[{server_name}] {tool.get('description', '')}",
                "inputSchema": tool.get("inputSchema", {}),
                "_server": server_name,
                "_original_name": tool["name"],
            }
        )

    return init_result, namespaced_tools


def _find_selected_tool(tools: List[Dict[str, Any]], tool_name: Optional[str]) -> Optional[Dict[str, Any]]:
    if not tool_name:
        return None

    exact_match = next((tool for tool in tools if tool.get("name") == tool_name), None)
    if exact_match:
        return exact_match

    original_name_matches = [tool for tool in tools if tool.get("_original_name") == tool_name]
    if len(original_name_matches) == 1:
        return original_name_matches[0]

    return None


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        print("Set it first, for example:", file=sys.stderr)
        print("  set OPENAI_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    local_endpoint = os.getenv("MCP_WEB_ENDPOINT", "http://127.0.0.1:8000/mcp")
    atlassian_endpoint = os.getenv("ATLASSIAN_MCP_WEB_ENDPOINT")
    if not atlassian_endpoint:
        print("Error: ATLASSIAN_MCP_WEB_ENDPOINT is not set.", file=sys.stderr)
        print("Set it first, for example:", file=sys.stderr)
        print("  set ATLASSIAN_MCP_WEB_ENDPOINT=https://your-atlassian-mcp.example.com/mcp", file=sys.stderr)
        sys.exit(1)

    clients = {
        "local": MCPWebClient(
            endpoint_url=local_endpoint,
            headers=_build_headers("MCP_WEB_API_KEY"),
        ),
        "atlassian": MCPWebClient(
            endpoint_url=atlassian_endpoint,
            headers=_build_headers("ATLASSIAN_MCP_WEB_API_KEY"),
        ),
    }
    router = OpenAIToolRouter()

    try:
        print(f"Connecting to local MCP web server at {local_endpoint}...")
        clients["local"].connect()

        print(f"Connecting to Atlassian MCP web server at {atlassian_endpoint}...")
        clients["atlassian"].connect()

        local_info, local_tools = _load_server_tools("local", clients["local"])
        atlassian_info, atlassian_tools = _load_server_tools("atlassian", clients["atlassian"])
        tools = local_tools + atlassian_tools

        print(f"Local server: {local_info['serverInfo']['name']} v{local_info['serverInfo']['version']}")
        print(
            f"Atlassian server: {atlassian_info['serverInfo']['name']} v{atlassian_info['serverInfo']['version']}"
        )

        print("\nAvailable tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        print("\nOpenAI-routed multi-server chatbot ready. Type a prompt (or 'tools' / 'exit').")
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
            selected_tool = _find_selected_tool(tools, tool_name)

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

            server_name = selected_tool["_server"]
            original_tool_name = selected_tool["_original_name"]
            client = clients[server_name]

            try:
                result = client.call_tool(original_tool_name, **arguments)
                print(
                    f"Assistant: Routed to '{selected_tool['name']}' (confidence={confidence}) with {arguments} -> {result}"
                )
            except Exception as tool_error:
                print(f"Assistant: Tool call failed: {tool_error}")

    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    finally:
        for client in clients.values():
            client.disconnect()


if __name__ == "__main__":
    main()
