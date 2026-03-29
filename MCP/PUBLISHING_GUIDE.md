# Publishing Your MCP Server

## Step 1: Local Installation for Testing

```bash
# Install in development mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

## Step 2: Configure for Claude Desktop

### Windows
1. Create/edit: `%APPDATA%\Claude\claude_config.json`
2. Add this configuration:

```json
{
  "mcpServers": {
    "mcp-test-server": {
      "command": "python",
      "args": ["-m", "mcp_test_server.server"],
      "env": {
        "PYTHONPATH": "C:\\Users\\mugil\\OneDrive\\python\\MCP"
      }
    }
  }
}
```

### macOS
Edit `~/.claude_desktop_config` and add the same configuration with appropriate paths.

### Linux
Edit `~/.config/Claude/claude_config.json`

## Step 3: Testing in Claude Desktop

1. Open Claude Desktop
2. Look for "Tools" section in the sidebar
3. Your MCP server's tools should appear:
   - add
   - multiply
   - get_server_info

## Step 4: Publishing to PyPI

### Prepare Your Package

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check package
twine check dist/*
```

### Create PyPI Account

1. Sign up at https://pypi.org/
2. Create API token at https://pypi.org/manage/account/tokens/
3. Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi_YOUR_TOKEN_HERE
```

### Upload to PyPI

```bash
# Upload to PyPI
twine upload dist/*

# Or use repository URL directly
twine upload -r pypi dist/*
```

## Step 5: Installation from PyPI

After publishing, users can install with:

```bash
pip install mcp-test-server
```

And configure Claude with:

```json
{
  "mcpServers": {
    "mcp-test-server": {
      "command": "mcp-test-server"
    }
  }
}
```

## Step 6: Version Updates

When updating:

1. Update version in `setup.py` and `mcp_test_server/__init__.py`
2. Rebuild: `python -m build`
3. Upload: `twine upload dist/*`

## Publishing to GitHub

1. Create repository on GitHub
2. Push code:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/mcp-test-server.git
git push -u origin main
```

3. Add GitHub releases for each version

## Alternative: Local GitHub Installation

Users can also install directly from GitHub:

```bash
pip install git+https://github.com/yourusername/mcp-test-server.git
```

## File Structure for Publishing

```
mcp-test-server/
├── mcp_test_server/
│   ├── __init__.py
│   └── server.py
├── setup.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## Recommended Files to Add

- **LICENSE**: Choose from MIT, Apache 2.0, etc.
- **.gitignore**: Standard Python .gitignore
- **MANIFEST.in**: If you have non-Python files to include

Example `.gitignore`:
```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.venv
venv/
```

## Verifying Installation in Claude

After configuration, restart Claude Desktop and check:

1. Settings → Integrations
2. Look for your MCP server in the connections list
3. Try using the tools in a conversation

## Troubleshooting

If tools don't appear:

1. Check Claude Desktop logs
2. Verify Python path is correct
3. Ensure server runs: `python -m mcp_test_server.server`
4. Check permissions on config file

## Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [PyPI Documentation](https://packaging.python.org/)
- [setuptools Reference](https://setuptools.pypa.io/)
