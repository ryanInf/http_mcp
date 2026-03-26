"""
HTTP 客户端 - 使用 HackRequests 库
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional, Any

from http_mcp.HackRequests import hackRequests
from http_mcp.parser import ParsedHTTPRequest


def strip_html_tags(text: str) -> str:
    """
    去除 HTML 标签，保留文本内容

    Args:
        text: 包含 HTML 标签的文本

    Returns:
        str: 去除 HTML 标签后的文本
    """
    if not text:
        return text

    # 去除 script 和 style 标签及其内容
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 去除所有 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)

    # 清理多余的空白字符
    text = re.sub(r'\s+', ' ', text).strip()

    return text


@dataclass
class HTTPResponse:
    """HTTP 响应对象"""
    status_code: int
    reason: str
    headers: Dict[str, str]
    body: str
    http_version: str


class HTTPClient:
    """HTTP 客户端，使用 HackRequests 库"""

    def __init__(self, timeout: int = 30, follow_redirects: bool = True,
                 verify_ssl: bool = True, http2: bool = False, http_proxy: str = None):
        """
        初始化 HTTP 客户端

        Args:
            timeout: 超时时间（秒）
            follow_redirects: 是否跟随重定向
            verify_ssl: 是否验证 SSL 证书 (HackRequests 默认不验证)
            http2: 是否使用 HTTP/2 (HackRequests 不支持)
            http_proxy: HTTP 代理地址 (如 http://127.0.0.1:8080)
        """
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.verify_ssl = verify_ssl
        self.http2 = http2
        self.http_proxy = http_proxy

        # 创建 HackRequests 实例
        from http_mcp.HackRequests import httpcon
        con = httpcon(timeout=timeout)
        self.hack = hackRequests(con)

    def _parse_proxy(self, proxy: str) -> Optional[tuple]:
        """解析代理字符串为 (host, port) 元组"""
        if not proxy:
            return None

        # 支持 http://host:port 格式
        if '://' in proxy:
            from urllib.parse import urlparse
            parsed = urlparse(proxy)
            return (parsed.hostname, parsed.port) if parsed.port else (parsed.hostname, 8080)
        else:
            # 简单 host:port 格式
            parts = proxy.split(':')
            if len(parts) == 2:
                return (parts[0], int(parts[1]))
        return None

    def send_request(self, parsed_request: ParsedHTTPRequest, strip_html: bool = False,
                     allow_custom_host: bool = False, allow_custom_content_length: bool = False,
                     custom_host_header: str = None) -> HTTPResponse:
        """
        发送 HTTP 请求

        Args:
            parsed_request: 解析后的请求对象
            strip_html: 是否去除响应中的 HTML 标签
            allow_custom_host: 是否允许自定义 Host 头部（默认使用 URL 中的 host）
            allow_custom_content_length: 是否允许自定义 Content-Length 头部（默认自动计算）
            custom_host_header: 自定义 Host 头部的值（用于 HTTP 头，不改变实际连接的 host）

        Returns:
            HTTPResponse: 响应对象

        Raises:
            Exception: 请求失败时抛出异常
        """
        # 解析代理
        proxy = self._parse_proxy(self.http_proxy)

        # 判断是否使用代理（需要在构建请求前判断）
        use_proxy = proxy is not None

        # 构建原始请求
        raw_request = self._build_raw_request(
            parsed_request,
            allow_custom_host=allow_custom_host,
            allow_custom_content_length=allow_custom_content_length,
            custom_host_header=custom_host_header,
            use_proxy=use_proxy
        )

        # 实际连接的 host（用于自定义 Host 头场景）
        real_host = None
        if allow_custom_host and custom_host_header:
            real_host = parsed_request.host  # 实际连接的 host

        # SSL 设置
        ssl = parsed_request.scheme == 'https'

        # 是否跟随重定向
        location = self.follow_redirects

        try:
            # 发送原始请求
            hack_resp = self.hack.httpraw(
                raw_request,
                proxy=proxy,
                real_host=real_host,
                ssl=ssl,
                location=location
            )

            # 获取响应体
            body = hack_resp.text()

            # 去除 HTML 标签
            if strip_html:
                body = strip_html_tags(body)

            # 构建响应
            return HTTPResponse(
                status_code=hack_resp.status_code,
                reason=hack_resp.rep.reason,
                headers=hack_resp.headers,
                body=body,
                http_version='HTTP/1.1'  # HackRequests 不支持 HTTP/2
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception(f"Request failed: {e}")

    def _build_raw_request(self, parsed_request: ParsedHTTPRequest,
                           allow_custom_host: bool = False,
                           allow_custom_content_length: bool = False,
                           custom_host_header: str = None,
                           use_proxy: bool = False) -> str:
        """
        构建原始 HTTP 请求字符串

        注意：HackRequests 使用 \n 作为行分隔符，而不是 \r\n

        Args:
            parsed_request: 解析后的请求对象
            allow_custom_host: 是否允许自定义 Host
            allow_custom_content_length: 是否允许自定义 Content-Length
            custom_host_header: 自定义 Host 头部的值
            use_proxy: 是否使用代理（代理模式下需要使用绝对URL）

        Returns:
            str: 原始 HTTP 请求字符串
        """
        # 请求行（使用 \n）
        # 注意：如果使用代理，需要使用绝对URL
        if use_proxy:
            # 代理模式下需要使用绝对URL
            scheme = parsed_request.scheme if parsed_request.scheme else 'http'
            # path 可能已包含查询字符串
            request_line = f"{parsed_request.method} {scheme}://{parsed_request.host}{parsed_request.path} {parsed_request.http_version}\n"
        else:
            request_line = f"{parsed_request.method} {parsed_request.path} {parsed_request.http_version}\n"

        # 构建头部
        header_lines = []
        for name, value in parsed_request.headers.items():
            name_lower = name.lower()

            # 跳过 Connection 头部，HackRequests 会自动处理
            if name_lower == 'connection':
                continue

            # 处理 Host 头部
            if name_lower == 'host':
                if allow_custom_host and custom_host_header:
                    header_lines.append(f"{name}: {custom_host_header}")
                else:
                    header_lines.append(f"{name}: {value}")
                continue

            # 处理 Content-Length 头部
            if name_lower == 'content-length':
                if allow_custom_content_length:
                    header_lines.append(f"{name}: {value}")
                # 否则跳过，让 HackRequests 自动计算
                continue

            header_lines.append(f"{name}: {value}")

        # 构建原始请求（使用 \n）
        headers_str = '\n'.join(header_lines)

        # 添加 body
        # 注意：HackRequests.httpraw 使用 raw.strip() 移除首尾空白
        # 当只有1个header时strip后会丢失末尾换行符导致解析失败
        # 因此需要添加额外的header（如User-Agent）确保至少有2行header
        if len(header_lines) < 2:
            if 'User-Agent' not in headers_str:
                headers_str += '\nUser-Agent: HTTP-MCP/1.0'

        if parsed_request.body:
            raw_request = f"{request_line}{headers_str}\n\n{parsed_request.body}"
        else:
            raw_request = f"{request_line}{headers_str}\n"

        return raw_request

    def send_raw_request(self, raw_request: str, http2: bool = False, strip_html: bool = False) -> HTTPResponse:
        """
        发送原始 HTTP 请求

        Args:
            raw_request: 原始 HTTP 请求报文
            http2: 是否使用 HTTP/2 (不支持)
            strip_html: 是否去除响应中的 HTML 标签

        Returns:
            HTTPResponse: 响应对象
        """
        from http_mcp.parser import HTTPRequestParser

        # 解析请求
        parsed_request = HTTPRequestParser.parse(raw_request)

        return self.send_request(parsed_request, strip_html=strip_html)


def format_response(response: HTTPResponse, max_body_length: int = 10000) -> str:
    """
    格式化响应为字符串

    Args:
        response: HTTP 响应
        max_body_length: 最大body长度

    Returns:
        str: 格式化的响应字符串
    """
    # 构建响应头
    header_lines = [f"HTTP/1.1 {response.status_code} {response.reason}"]

    for name, value in response.headers.items():
        header_lines.append(f"{name}: {value}")

    # 构建响应体（可能截断）
    body = response.body
    if len(body) > max_body_length:
        body = body[:max_body_length] + f"\n... (truncated, total {len(response.body)} bytes)"

    return '\r\n'.join(header_lines) + '\r\n\r\n' + body


def test_client():
    """测试 HTTP 客户端"""
    client = HTTPClient(timeout=10)

    # 测试 HTTP/1.1 请求
    raw_request = "GET / HTTP/1.1\r\nHost: httpbin.org\r\nUser-Agent: Mozilla/5.0\r\n\r\n"

    try:
        response = client.send_raw_request(raw_request)
        print(f"Status: {response.status_code}")
        print(f"Body length: {len(response.body)}")
        print(f"First 200 chars: {response.body[:200]}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    test_client()
