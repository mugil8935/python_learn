# Remote MCP Server Setup

## Scenario: MCP Server Running on Separate Machine

Use these configurations depending on your deployment setup.

---

## Setup 1: HTTP Server (Easiest for Network Separation)

### On Remote Machine (Server)

```bash
cd /path/to/mcp
python -m mcp_test_server.http_server
# Server runs on http://0.0.0.0:8000
```

Or specify custom port:
```bash
python -m mcp_test_server.http_server --port 9000
```

### On Local Machine (Claude Desktop)

**Claude config.json:**
```json
{
  "mcpServers": {
    "test-server": {
      "command": "python",
      "args": [
        "-m", 
        "mcp_test_server.http_client",
        "--url",
        "http://remote-machine.com:8000"
      ]
    }
  }
}
```

**Replace:**
- `remote-machine.com` with your server's IP/hostname
- `8000` with the port if different

---

## Setup 2: SSH Tunnel (Secure, uses stdio)

### On Remote Machine (Server)

```bash
cd /path/to/mcp
python -m mcp_test_server.server
```

### On Local Machine (Claude Desktop)

**Claude config.json:**
```json
{
  "mcpServers": {
    "test-server": {
      "command": "ssh",
      "args": [
        "username@remote-machine.com",
        "cd /path/to/mcp && python -m mcp_test_server.server"
      ]
    }
  }
}
```

**Setup SSH:**
1. Ensure SSH access to remote machine
2. Configure SSH key authentication (no password prompt)
3. Verify: `ssh username@remote-machine.com "echo connected"`

---

## Setup 3: Docker Container

### Dockerfile (for remote machine)

```dockerfile
FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY mcp_test_server/ ./mcp_test_server/

# Run HTTP server on port 8000
CMD ["python", "-m", "mcp_test_server.http_server", "--host", "0.0.0.0", "--port", "8000"]
```

### Run Container

```bash
docker build -t mcp-test-server .
docker run -p 8000:8000 mcp-test-server
```

### Claude Config (local machine)

```json
{
  "mcpServers": {
    "test-server": {
      "command": "python",
      "args": [
        "-m",
        "mcp_test_server.http_client",
        "--url",
        "http://docker-host:8000"
      ]
    }
  }
}
```

---

## Setup 4: Kubernetes (Production)

Create a deployment and service on your K8s cluster, then use the service URL in Claude config.

---

## Comparison

| Method | Pros | Cons |
|--------|------|------|
| HTTP Server | Simple, stateless, scalable | Less secure (HTTP) |
| SSH Tunnel | Secure, uses stdio directly | Requires SSH key setup |
| Docker | Containerized, portable | Extra layer of abstraction |
| Kubernetes | Production-ready, scalable | Complex setup |

---

## Testing Connection

### Test HTTP Server

```bash
# On local machine
curl -X POST http://remote-machine.com:8000/tools/list

# Should return list of available tools
```

### Test SSH Connection

```bash
# Verify SSH works
ssh username@remote-machine.com "python -m mcp_test_server.server"

# If it runs without error, SSH setup is correct
```

---

## Troubleshooting

### HTTP Server Not Responding
- Check firewall: `telnet remote-machine.com 8000`
- Verify server is running: `ps aux | grep http_server`
- Check logs for errors

### SSH Connection Fails
- Verify SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
- Test connection: `ssh -v username@remote-machine.com`
- Check known_hosts file

### Tools Not Appearing in Claude
- Restart Claude Desktop
- Check Claude logs in `%APPDATA%\Claude\logs\`
- Verify URL/connection in config

---

## Security Considerations

### HTTP
- Use HTTPS in production: Add reverse proxy (nginx) with SSL
- Add authentication: Modify http_server.py to require API keys
- Firewall: Only allow access from trusted IPs

### SSH
- Use key-based authentication only
- Disable password login on remote server
- Use non-standard ports (22 is default, change if possible)

---

## Example: Nginx Reverse Proxy for HTTPS

```nginx
server {
    listen 443 ssl;
    server_name remote-machine.com;
    
    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

Then use `https://remote-machine.com` in Claude config.

---

## Windows Remote Machine Example

### On Windows Server (Remote)

```powershell
# Install Python and dependencies
pip install -r requirements.txt

# Run HTTP server
python -m mcp_test_server.http_server
```

### On Local Claude Desktop

Same HTTP config as above, pointing to Windows machine IP.

---

## Production Checklist

- [ ] SSL/HTTPS configured
- [ ] Authentication enabled
- [ ] Firewall rules configured
- [ ] Monitoring/logging enabled
- [ ] Health check endpoint added
- [ ] Error handling robust
- [ ] Rate limiting configured
- [ ] Documentation updated
