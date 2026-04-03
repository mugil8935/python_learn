# MCP Server and Client Implementation

This is a test implementation of the Model Context Protocol (MCP) with a basic server and client.

## Architecture

```
MCP Client                MCP Server
    |                         |
    |-- JSON-RPC (stdin) ---->|
    |<-- JSON-RPC (stdout) ---|
    |                         |
```

## Files

- **mcp_server.py**: MCP server implementation that provides tools and handles requests
- **mcp_server_web.py**: Web-exposed MCP server (HTTP JSON-RPC) built with FastAPI
- **mcp_client.py**: MCP client implementation that connects to the server and calls tools
- **openai/mcp_client_openai.py**: MCP chatbot client that uses OpenAI to route prompts to tools semantically
- **openai/mcp_client_openai_web.py**: MCP chatbot client that uses OpenAI routing and calls MCP web endpoint
- **openai/mcp_client_openai_multi_web.py**: MCP chatbot client that routes across local MCP web tools and Atlassian MCP web tools

## Features

### Server Features
- Registers tools with input schemas
- Handles JSON-RPC requests
- Provides built-in tools: `add`, `multiply`, `get_info`
- Extensible tool registration system

### Client Features
- Connects to server via subprocess
- Sends JSON-RPC requests
- Lists available tools
- Calls tools with arguments
- Error handling

## Built-in Tools

### add
Adds two numbers together
- Parameters: `a` (number), `b` (number)
- Returns: Sum of a and b

### multiply
Multiplies two numbers
- Parameters: `a` (number), `b` (number)
- Returns: Product of a and b

### get_info
Returns information about the server
- Parameters: None
- Returns: Server name, version, and number of available tools

## Usage

### Running the Server Alone

```bash
python mcp_server.py
```

The server will read JSON-RPC requests from stdin and write responses to stdout.

### Running Web-Exposed MCP Server

```bash
python mcp_server_web.py
```

Server endpoints:
- `GET /health`
- `POST /mcp` (JSON-RPC 2.0 payload)

Example request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

### Running Client Example

```bash
python mcp_client.py
```

This will:
1. Start a server process
2. Connect to it
3. Initialize the connection
4. List available tools
5. Call some example tools
6. Disconnect

### Running OpenAI-Routed Chatbot Client

Set your OpenAI API key, then run:

```bash
set OPENAI_API_KEY=your_key_here
python openai/mcp_client_openai.py
```

Optional model override:

```bash
set OPENAI_MODEL=gpt-4.1-mini
```

This client sends your prompt and the MCP tool list to OpenAI, gets the selected tool + arguments, and then calls that tool on the MCP server.

### Running OpenAI-Routed Chatbot Client (Web MCP)

First run the web server:

```bash
python mcp_server_web.py
```

Then in another terminal:

```bash
set OPENAI_API_KEY=your_key_here
set MCP_WEB_ENDPOINT=http://127.0.0.1:8000/mcp
python openai/mcp_client_openai_web.py
```

### Running OpenAI-Routed Multi-Server Chatbot Client

This version merges tools from both your local MCP web server and an Atlassian MCP web server.

```bash
set OPENAI_API_KEY=your_key_here
set MCP_WEB_ENDPOINT=http://127.0.0.1:8000/mcp
set ATLASSIAN_MCP_WEB_ENDPOINT=https://your-atlassian-mcp.example.com/mcp
python openai/mcp_client_openai_multi_web.py
```

Optional auth headers:

```bash
set MCP_WEB_API_KEY=your_local_server_key
set ATLASSIAN_MCP_WEB_API_KEY=your_atlassian_server_key
```

## JSON-RPC Protocol Examples

### Initialize Request
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {}
}
```

### List Tools Request
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### Call Tool Request
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {"a": 5, "b": 3}
  }
}
```

## Extending the Server

To add a new tool to the server:

```python
def my_custom_tool(param1: str, param2: int) -> str:
    return f"{param1}: {param2}"

server.register_tool(
    name="custom",
    description="My custom tool",
    input_schema={
        "param1": {"type": "string", "description": "First parameter"},
        "param2": {"type": "integer", "description": "Second parameter"}
    },
    handler=my_custom_tool
)
```

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
