"""
测试 HTTP MCP 服务器
"""
import json
from http_mcp import server as mcp_server
from http_mcp.security import SecurityConfig, SecurityValidator


def test_tools_list():
    """测试获取工具列表"""
    # FastMCP 工具列表需要通过其接口获取
    print("=== Tools List ===")
    print("Tools: http_send_request, http_build_request")
    print()


def test_http_build_request():
    """测试构建请求"""
    result = mcp_server.http_build_request(
        method="POST",
        url="https://httpbin.org/post",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "HTTP-MCP/1.0"
        },
        body='{"test": "value"}'
    )

    print("=== Build Request ===")
    print(json.dumps(result, indent=2))
    print()


def test_http_send_request():
    """测试发送请求"""
    # 原始 HTTP 请求
    raw_request = """POST /post HTTP/1.1
Host: httpbin.org
Content-Type: application/json
User-Agent: HTTP-MCP/1.0
Accept: */*

{"test": "value", "name": "test"}"""

    result = mcp_server.http_send_request(
        content=raw_request,
        baseurl="https://httpbin.org",
        timeout=30
    )

    print("=== Send Request ===")
    print(f"Status: {result.get('status_code')}")
    print(f"Body length: {result.get('body_length')}")
    print(f"HTTP Version: {result.get('http_version')}")
    print()
    print("First 500 chars of body:")
    print(result.get('body', '')[:500])
    print()


def test_security_blocked():
    """测试安全拦截"""
    # 测试正常请求（默认配置允许所有域名）
    # 注意：HackRequests.httpraw 使用 raw.strip()，末尾不能有多余空行
    raw_request = """GET / HTTP/1.1
Host: httpbin.org
"""

    result = mcp_server.http_send_request(
        content=raw_request,
        baseurl="https://httpbin.org"
    )

    print("=== Security Test ===")
    print(f"Status: {result.get('status_code')}")
    print(f"Blocked: {result.get('blocked', False)}")
    print(f"Error: {result.get('error')}")
    print()


def test_strip_html():
    """测试 HTML 标签去除功能"""
    # 使用 httpbin.org/html 返回 HTML 内容
    raw_request = """GET /html HTTP/1.1
Host: httpbin.org
User-Agent: HTTP-MCP/1.0

"""

    # 不去除 HTML 标签
    result = mcp_server.http_send_request(
        content=raw_request,
        baseurl="https://httpbin.org",
        strip_html=False
    )

    print("=== Without strip_html ===")
    print(f"Body length: {result.get('body_length')}")
    print(f"First 200 chars: {result.get('body', '')[:200]}")
    print()

    # 去除 HTML 标签
    result = mcp_server.http_send_request(
        content=raw_request,
        baseurl="https://httpbin.org",
        strip_html=True
    )

    print("=== With strip_html ===")
    print(f"Body length: {result.get('body_length')}")
    print(f"Body: {result.get('body', '')}")
    print()


if __name__ == '__main__':
    test_tools_list()
    test_http_build_request()
    test_http_send_request()
    test_security_blocked()
    test_strip_html()
