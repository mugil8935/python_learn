"""
MCP Client Chatbot with Langchain Tool Router
Uses Langchain LLM to semantically choose the best MCP tool and arguments.
"""

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Union

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


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

    def route_and_execute(self, user_prompt: str, mcp_client: "MCPClient", tools: List[Dict[str, Any]]) -> str:
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
    """Interactive MCP chatbot with Langchain agent routing"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        print("Set it first, for example:", file=sys.stderr)
        print("  set OPENAI_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    project_root = os.path.dirname(os.path.dirname(__file__))
    server_path = os.path.join(project_root, "mcp_server.py")
    client = MCPClient(server_command=[sys.executable, server_path])
    router = LangchainMCPRouter()

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

        print("\nLangchain-routed chatbot ready. Type a prompt (or 'tools' / 'exit').")
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
