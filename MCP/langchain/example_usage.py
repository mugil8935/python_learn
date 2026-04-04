"""
Example usage of Langchain MCP clients.
Demonstrates how to use the different transport modes.
"""

import os
import sys
from typing import Optional


def example_local_transport():
    """Example: Using local subprocess transport"""
    print("=" * 60)
    print("Example 1: Local Subprocess Transport")
    print("=" * 60)
    
    from mcp_client_langchain import MCPClient, LangchainMCPRouter

    # Set up environment
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Skipping example.")
        return

    project_root = os.path.dirname(os.path.dirname(__file__))
    server_path = os.path.join(project_root, "mcp_server.py")

    client = MCPClient(server_command=[sys.executable, server_path])
    router = LangchainMCPRouter()

    try:
        print("Connecting to MCP server...")
        client.connect()
        
        print("Initializing...")
        init_result = client.initialize()
        print(f"✓ Server: {init_result['serverInfo']['name']} v{init_result['serverInfo']['version']}")

        tools = client.list_tools()
        print(f"✓ Available tools: {len(tools)}")
        for tool in tools[:3]:  # Show first 3
            print(f"  - {tool['name']}")

        # Example query
        print("\nExample query: 'What tools are available?'")
        result = router.route_and_execute("Give me a summary of available tools", client)
        print(f"Result: {result[:200]}...")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        client.disconnect()
        print()


def example_web_transport():
    """Example: Using HTTP web transport"""
    print("=" * 60)
    print("Example 2: HTTP Web Transport")
    print("=" * 60)
    
    from mcp_client_langchain_web import MCPWebClient, LangchainMCPRouter

    # Set up environment
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Skipping example.")
        return

    endpoint = os.getenv("MCP_WEB_ENDPOINT", "http://127.0.0.1:8000/mcp")
    client = MCPWebClient(endpoint_url=endpoint)
    router = LangchainMCPRouter()

    try:
        print(f"Connecting to MCP web server at {endpoint}...")
        client.connect()
        
        print("Initializing...")
        init_result = client.initialize()
        print(f"✓ Server: {init_result['serverInfo']['name']} v{init_result['serverInfo']['version']}")

        tools = client.list_tools()
        print(f"✓ Available tools: {len(tools)}")
        for tool in tools[:3]:  # Show first 3
            print(f"  - {tool['name']}")
        
        print("Note: To test, ensure the web server is running at the endpoint.")
        
    except Exception as e:
        print(f"✗ Error: {e} (This is expected if web server is not running)")
    finally:
        client.disconnect()
        print()


def example_multi_server_transport():
    """Example: Using multi-server HTTP web transport"""
    print("=" * 60)
    print("Example 3: Multi-Server HTTP Web Transport")
    print("=" * 60)
    
    from mcp_client_langchain_multi_web import MCPWebClient, LangchainMCPRouter, _load_server_tools

    # Set up environment
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Skipping example.")
        return

    local_endpoint = os.getenv("MCP_WEB_ENDPOINT", "http://127.0.0.1:8000/mcp")
    atlassian_endpoint = os.getenv("ATLASSIAN_MCP_WEB_ENDPOINT")

    if not atlassian_endpoint:
        print("⚠️  ATLASSIAN_MCP_WEB_ENDPOINT not set. Skipping example.")
        print("   Set this to test multi-server functionality.")
        return

    clients = {
        "local": MCPWebClient(endpoint_url=local_endpoint),
        "atlassian": MCPWebClient(endpoint_url=atlassian_endpoint),
    }
    router = LangchainMCPRouter()

    try:
        print(f"Connecting to local server at {local_endpoint}...")
        clients["local"].connect()
        
        print(f"Connecting to Atlassian server at {atlassian_endpoint}...")
        clients["atlassian"].connect()

        print("Loading tools from both servers...")
        local_info, local_tools = _load_server_tools("local", clients["local"])
        atlassian_info, atlassian_tools = _load_server_tools("atlassian", clients["atlassian"])
        
        print(f"✓ Local server: {local_info['serverInfo']['name']} v{local_info['serverInfo']['version']}")
        print(f"  Tools: {len(local_tools)}")
        print(f"✓ Atlassian server: {atlassian_info['serverInfo']['name']} v{atlassian_info['serverInfo']['version']}")
        print(f"  Tools: {len(atlassian_tools)}")
        
    except Exception as e:
        print(f"✗ Error: {e} (This is expected if servers are not running)")
    finally:
        for client in clients.values():
            client.disconnect()
        print()


def main():
    """Run all examples"""
    print("\n")
    print("🚀 Langchain MCP Client Examples")
    print("=" * 60)
    print()
    
    example_local_transport()
    example_web_transport()
    example_multi_server_transport()
    
    print("=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
