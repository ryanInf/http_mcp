"""
HTTP 请求解析器 - 解析原始 HTTP 请求报文
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse


@dataclass
class ParsedHTTPRequest:
    """解析后的 HTTP 请求"""
    method: str
    path: str
    http_version: str
    headers: Dict[str, str]
    body: Optional[str]
    host: str
    scheme: str
    port: Optional[int]


class HTTPRequestParser:
    """HTTP 请求报文解析器"""

    # HTTP 方法
    HTTP_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE', 'CONNECT'}

    # 常用的 HTTP 头部
    COMMON_HEADERS = {
        'Host', 'User-Agent', 'Accept', 'Accept-Language', 'Accept-Encoding',
        'Content-Type', 'Content-Length', 'Authorization', 'Cookie',
        'Referer', 'Origin', 'X-Requested-With', 'X-Forwarded-For',
        'X-Real-IP', 'Connection', 'Upgrade-Insecure-Requests'
    }

    @classmethod
    def parse(cls, raw_request: str) -> ParsedHTTPRequest:
        """
        解析原始 HTTP 请求报文

        Args:
            raw_request: 原始 HTTP 请求报文

        Returns:
            ParsedHTTPRequest: 解析后的请求对象

        Raises:
            ValueError: 请求格式错误
        """
        if not raw_request or not raw_request.strip():
            raise ValueError("Empty request")

        # 统一换行符为 \r\n
        normalized = raw_request.replace('\n', '\r\n').replace('\r\r\n', '\r\n')
        lines = normalized.strip().split('\r\n')
        if len(lines) < 1:
            raise ValueError("Invalid request format")

        # 解析请求行
        request_line = lines[0]
        parts = request_line.split(' ')

        if len(parts) < 2:
            # 尝试处理只有两个部分的情况（可能没有 HTTP 版本）
            if len(parts) == 2:
                method, path = parts
                http_version = 'HTTP/1.1'
            else:
                raise ValueError(f"Invalid request line: {request_line}")
        else:
            method, path, http_version = parts[0], parts[1], parts[2]

        if method not in cls.HTTP_METHODS:
            raise ValueError(f"Invalid HTTP method: {method}")

        # 解析头部
        headers = {}
        body_start_idx = 1

        for i in range(1, len(lines)):
            line = lines[i]
            if line == '':
                body_start_idx = i + 1
                break

            # 解析头部行
            if ':' in line:
                # 找到第一个冒号的位置
                colon_idx = line.index(':')
                header_name = line[:colon_idx].strip()
                header_value = line[colon_idx + 1:].strip()
                headers[header_name] = header_value

        # 解析消息体
        body = None
        if body_start_idx < len(lines):
            body_lines = lines[body_start_idx:]

            # 检查是否是 multipart/form-data
            content_type = headers.get('Content-Type', '')
            is_multipart = 'multipart/form-data' in content_type.lower()

            if is_multipart:
                # 对于 multipart/form-data，保留所有行（包括空行）
                # 因为空行是 multipart 格式中分隔 header 和 content 的关键
                body = '\r\n'.join(body_lines)
            else:
                # 过滤掉空行
                non_empty_lines = [line for line in body_lines if line.strip()]
                if non_empty_lines:
                    first_line = non_empty_lines[0]
                    # 如果以 { [ < 开头，或者是纯数字，认为是 body
                    # 否则检查是否符合 HTTP header 格式
                    if first_line.strip().startswith(('{', '[', '<')) or first_line.strip().isdigit():
                        body = '\r\n'.join(non_empty_lines)
                    elif ':' in first_line:
                        # HTTP header 格式: "Header-Name: value"
                        # 检查是否符合标准 header 格式（冒号前无空格，冒号后有空格）
                        colon_idx = first_line.index(':')
                        header_name = first_line[:colon_idx].strip()
                        header_value = first_line[colon_idx + 1:].strip()
                        # 如果冒号前是单个单词（header 名称格式）且冒号后有内容，认为是 header
                        if ' ' not in header_name and header_value:
                            body = None
                        else:
                            body = '\r\n'.join(non_empty_lines)
                    else:
                        body = '\r\n'.join(non_empty_lines)

        # 提取 host、scheme 和 port
        host = headers.get('Host', '')
        if not host:
            raise ValueError("Missing Host header")

        # 解析 host（可能包含端口）
        if ':' in host:
            host, port_str = host.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 80 if headers.get('scheme', 'http') == 'http' else 443
        else:
            port = None

        # 判断 scheme
        scheme = 'https' if headers.get('scheme') == 'https' else 'http'
        # 检查是否使用 HTTPS（通过端口或请求行判断）
        if port == 443:
            scheme = 'https'
        elif port == 80 or port is None:
            scheme = 'http'

        return ParsedHTTPRequest(
            method=method,
            path=path,
            http_version=http_version,
            headers=headers,
            body=body,
            host=host,
            scheme=scheme,
            port=port
        )

    @classmethod
    def build_raw_request(cls, method: str, path: str, headers: Dict[str, str],
                          body: Optional[str] = None, http_version: str = 'HTTP/1.1') -> str:
        """
        构建原始 HTTP 请求报文

        Args:
            method: HTTP 方法
            path: 请求路径
            headers: 请求头
            body: 请求体
            http_version: HTTP 版本

        Returns:
            str: 原始请求报文
        """
        # 构建请求行
        request_line = f"{method} {path} {http_version}\r\n"

        # 构建头部
        header_lines = []
        for name, value in headers.items():
            header_lines.append(f"{name}: {value}")

        # 构建请求
        raw_request = request_line + '\r\n'.join(header_lines)

        # 添加消息体
        if body:
            raw_request += '\r\n\r\n' + body
        else:
            raw_request += '\r\n'

        return raw_request


def test_parser():
    """测试解析器"""
    # 测试 HTTP/1.1 请求
    raw_request = """GET /api/users HTTP/1.1
Host: example.com
User-Agent: Mozilla/5.0
Accept: */*
Content-Type: application/json

{"name": "test"}"""

    parsed = HTTPRequestParser.parse(raw_request)
    print(f"Method: {parsed.method}")
    print(f"Path: {parsed.path}")
    print(f"Host: {parsed.host}")
    print(f"Scheme: {parsed.scheme}")
    print(f"Headers: {parsed.headers}")
    print(f"Body: {parsed.body}")


if __name__ == '__main__':
    test_parser()
