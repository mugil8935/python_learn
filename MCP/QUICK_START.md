# Quick Start: Add MCP Server to Claude Desktop

## Option 1: Local Setup (Quickest for Testing)

### Windows
1. Open `%APPDATA%\Claude\claude_config.json`
2. Add this config:

```json
{
  "mcpServers": {
    "test-server": {
      "command": "python",
      "args": ["-m", "mcp_test_server.server"],
      "env": {
        "PYTHONPATH": "C:\\Users\\mugil\\OneDrive\\python\\MCP"
      }
    }
  }
}
```

3. Restart Claude Desktop
4. Your tools will appear in Claude's tool menu

## Option 2: Install Package Locally

```bash
cd c:\Users\mugil\OneDrive\python\MCP
pip install -e .

# Then in Claude config:
{
  "mcpServers": {
    "test-server": {
      "command": "mcp-test-server"
    }
  }
}
```

## Option 3: Publish to PyPI (For Distribution)

### Step 1: Install build tools
```bash
pip install build twine
```

### Step 2: Update setup.py
Edit `setup.py` with your GitHub URL and details

### Step 3: Build
```bash
python -m build
```

### Step 4: Create PyPI account and upload
```bash
twine upload dist/*
```

### Step 5: Anyone can install globally
```bash
pip install mcp-test-server
```

## Verify It Works

After restarting Claude Desktop:
- You should see your MCP server listed
- Try asking Claude to use the "add" or "multiply" tools
- Example: "Use the add tool to calculate 5 + 3"

## File Locations

- **Windows Claude config**: `C:\Users\[username]\AppData\Roaming\Claude\claude_config.json`
- **macOS Claude config**: `~/.claude_desktop_config`
- **Linux Claude config**: `~/.config/Claude/claude_config.json`

See [PUBLISHING_GUIDE.md](PUBLISHING_GUIDE.md) for detailed publishing instructions.
