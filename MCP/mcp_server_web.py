"""
MCP Web Server
Exposes the existing MCPServer via HTTP using FastAPI.
"""

from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from mcp_server import MCPServer


app = FastAPI(title="MCP Web Server", version="1.0.0")
server = MCPServer()


@app.get("/health")
def health() -> Dict[str, str]:
    """Simple health check endpoint"""
    return {"status": "ok"}


@app.post("/mcp")
def mcp(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP JSON-RPC requests over HTTP"""
    if request.get("jsonrpc") != "2.0":
        raise HTTPException(status_code=400, detail="Only JSON-RPC 2.0 is supported")

    if "method" not in request:
        raise HTTPException(status_code=400, detail="Missing 'method' in request")

    normalized_request = {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "method": request.get("method"),
        "params": request.get("params", {}),
    }
    return server.handle_request(normalized_request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mcp_server_web:app", host="0.0.0.0", port=8000, reload=False)
