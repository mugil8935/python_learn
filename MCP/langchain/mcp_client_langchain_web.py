"""
MCP Client Chatbot with Langchain Agent Tool Router (Web Transport)
Routes prompts with Langchain and calls MCP tools over HTTP JSON-RPC.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class MCPWebClient:
    """MCP Client for communicating with MCP web server via HTTP JSON-RPC"""

    def __init__(self, endpoint_url: Optional[str] = None, timeout_seconds: int = 30):
        self.endpoint_url = endpoint_url or os.getenv("MCP_WEB_ENDPOINT", "http://127.0.0.1:8000/mcp")
        self.timeout_seconds = timeout_seconds
        self.request_id = 0
        self.available_tools: List[Dict[str, Any]] = []

    def connect(self):
        """Validate server connectivity"""
        health_url = self.endpoint_url.rsplit("/", 1)[0] + "/health"
        try:
            response = requests.get(health_url, timeout=self.timeout_seconds)
            response.raise_for_status()
        except Exception as error:
            raise RuntimeError(f"Cannot connect to MCP web server at {health_url}: {error}")

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
            )
            response.raise_for_status()
        except Exception as error:
            raise RuntimeError(f"HTTP request failed: {error}")

        try:
            response_json = response.json()
        except Exception as error:
            raise RuntimeError(f"Invalid JSON response from server: {error}")

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


class LangchainMCPRouter:
    """Use Langchain LLM to map user prompts to MCP tool calls"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            temperature=0,
        )

    def route(self, user_prompt: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to decide which tool to call"""
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

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(user_payload)),
        ]

        response = self.llm.invoke(messages)
        content = response.content or "{}"
        
        try:
            decision = json.loads(content)
        except json.JSONDecodeError:
            decision = {}

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

    def route_and_execute(self, user_prompt: str, mcp_client: MCPWebClient, tools: List[Dict[str, Any]]) -> str:
        """Route prompt and execute the chosen tool"""
        try:
            route = self.route(user_prompt, tools)
        except Exception as e:
            return f"Router error: {str(e)}"

        tool_name = route.get("tool_name")
        confidence = route.get("confidence", 0)
        clarification_question = route.get("clarification_question", "")
        arguments = route.get("arguments", {})

        selected_tool = next((t for t in tools if t.get("name") == tool_name), None)
        if not selected_tool:
            if clarification_question:
                return f"Clarification needed: {clarification_question}"
            else:
                return "Could not confidently choose a tool. Please be more specific."

        try:
            result = mcp_client.call_tool(tool_name, **arguments)
            return f"Tool '{tool_name}' (confidence={confidence}): {json.dumps(result) if not isinstance(result, str) else result}"
        except Exception as e:
            return f"Tool execution failed: {str(e)}"


def main():
    """Interactive MCP chatbot with Langchain agent routing (Web transport)"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        print("Set it first, for example:", file=sys.stderr)
        print("  set OPENAI_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    endpoint = os.getenv("MCP_WEB_ENDPOINT", "http://127.0.0.1:8000/mcp")
    client = MCPWebClient(endpoint_url=endpoint)
    router = LangchainMCPRouter()

    try:
        print(f"Connecting to MCP web server at {endpoint}...")
        client.connect()

        print("Initializing...")
        init_result = client.initialize()
        print(f"Server: {init_result['serverInfo']['name']} v{init_result['serverInfo']['version']}")

        tools = client.list_tools()
        print("\nAvailable tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        print("\nLangchain-routed web chatbot ready. Type a prompt (or 'tools' / 'exit').")
        while True:
            user_prompt = input("\nYou: ").strip()
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
                result = router.route_and_execute(user_prompt, client, tools)
                print(f"Assistant: {result}")
            except Exception as error:
                print(f"Assistant: Error: {error}")

    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
