"""
Claude Desktop Configuration Guide

To integrate your MCP server with Claude Desktop:

1. Create/edit: ~/.claude_desktop_config (macOS/Linux) or
   %APPDATA%\Claude\claude_config.json (Windows)

2. Add the following configuration:
"""

example_config = {
    "mcpServers": {
        "mcp-test-server": {
            "command": "python",
            "args": ["-m", "mcp_test_server.server"],
            "env": {}
        }
    }
}

# Alternative if published to PyPI:
example_config_pip = {
    "mcpServers": {
        "mcp-test-server": {
            "command": "mcp-test-server",
            "env": {}
        }
    }
}

print("Configuration example:")
import json
print(json.dumps(example_config, indent=2))
