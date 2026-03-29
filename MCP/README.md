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
- **mcp_client.py**: MCP client implementation that connects to the server and calls tools

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
