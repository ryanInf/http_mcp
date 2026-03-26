"""
HTTP MCP - HTTP 请求工具

类似 BurpSuite MCP 的 HTTP 请求工具，支持 HTTP/1.1 和 HTTP/2

Usage:
    python -m http_mcp.server

MCP 协议通过 stdio 进行通信
"""
from .client import HTTPClient, HTTPResponse
from .parser import HTTPRequestParser, ParsedHTTPRequest
from .security import SecurityValidator, SecurityConfig, create_default_validator

__version__ = "1.0.0"

__all__ = [
    "HTTPClient",
    "HTTPResponse",
    "HTTPRequestParser",
    "ParsedHTTPRequest",
    "SecurityValidator",
    "SecurityConfig",
    "create_default_validator",
]
