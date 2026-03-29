"""Setup configuration for MCP Test Server"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp-test-server",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A test MCP server implementation for Claude integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mcp-test-server",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "mcp>=0.1.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-test-server=mcp_test_server.server:main",
        ],
    },
)
