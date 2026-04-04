# Langchain MCP Clients

This folder contains Langchain-based MCP client implementations that use **LangChain agents** instead of the OpenAI library's raw JSON-RPC routing.

## Files

### `mcp_client_langchain.py`
- **Local Subprocess Transport**: Connects to MCP server via subprocess (local execution)
- Uses Langchain's ReAct agent pattern for intelligent tool selection
- Best for: Local development and testing

### `mcp_client_langchain_web.py`
- **HTTP Web Transport**: Connects to MCP server via HTTP JSON-RPC endpoint
- Single server support
- Best for: Cloud-hosted or remote MCP servers

### `mcp_client_langchain_multi_web.py`
- **Multi-Server HTTP Web Transport**: Connects to multiple MCP servers over HTTP
- Namespace support (e.g., `local:tool_name`, `atlassian:search_issue`)
- Best for: Orchestrating tools from multiple MCP servers

## Key Differences vs OpenAI Implementation

| Feature | OpenAI | Langchain |
|---------|--------|-----------|
| Routing | Manual JSON-RPC calls with structured output | Langchain agents with ReAct pattern |
| Agent Type | Semantic router | ReAct agent (Reasoning + Acting) |
| Tool Definition | Manual tool catalog creation | Langchain Tool objects |
| Execution | Direct tool calling | AgentExecutor with step-by-step reasoning |
| Extensibility | Raw control | Langchain ecosystem integrations |

## Installation

Install required dependencies:

```bash
pip install langchain langchain-openai
```

## Usage

### Local Transport Example

```bash
set OPENAI_API_KEY=your_key_here
python mcp_client_langchain.py
```

### Web Transport Example

```bash
set OPENAI_API_KEY=your_key_here
set MCP_WEB_ENDPOINT=http://127.0.0.1:8000/mcp
python mcp_client_langchain_web.py
```

### Multi-Server Example

```bash
set OPENAI_API_KEY=your_key_here
set MCP_WEB_ENDPOINT=http://127.0.0.1:8000/mcp
set ATLASSIAN_MCP_WEB_ENDPOINT=https://your-atlassian-mcp.example.com/mcp
python mcp_client_langchain_multi_web.py
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: LLM model to use (default: `gpt-4o-mini`)
- `MCP_WEB_ENDPOINT`: Primary MCP web server endpoint (default: `http://127.0.0.1:8000/mcp`)
- `MCP_WEB_API_KEY`: Optional Bearer token for primary server
- `ATLASSIAN_MCP_WEB_ENDPOINT`: Atlassian MCP server endpoint (required for multi-server)
- `ATLASSIAN_MCP_WEB_API_KEY`: Optional Bearer token for Atlassian server

## How It Works

1. **Agent Creation**: Langchain converts MCP tools into `Tool` objects
2. **ReAct Loop**: The agent uses a reasoning + acting pattern:
   - Thinking about which tool to use
   - Taking action by calling the tool
   - Observing the result
   - Repeating until a final answer is reached
3. **Tool Execution**: MCP tools are called via JSON-RPC (local or HTTP)
4. **Response**: The agent synthesizes a natural language response

## Advantages

- **Multi-step Reasoning**: Agents can reason through complex problems
- **Error Handling**: Built-in handling for parsing errors and invalid tools
- **Extensibility**: Easy to add custom agents, memory, or callbacks
- **Integration**: Works with other Langchain components (chains, memory, callbacks)
- **Better NLP**: Langchain's prompt engineering is tailored for reasoning tasks
