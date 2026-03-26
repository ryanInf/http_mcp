#!/usr/bin/env python3
# -*- coding:utf-8 -*-
###
# #      File: server.py
# #      Project: http_mcp
# #      Created Date: Thu Mar 26 2026
# #      Author: Ryan
# #      mail: ryaninf@outlook.com
# #      github: https://github.com/ryanInf
# #      Last Modified: 
# #      Modified By: 
# #------------------------------------------
# #      Copyright (c) 2026  
# #------------------------------------------
# #
###
"""
HTTP MCP 服务器 - 使用 FastMCP 重构
"""
import json
import os
import re
import time
from typing import Optional
from fastmcp import FastMCP
from http_mcp.client import HTTPClient, format_response
from http_mcp.parser import HTTPRequestParser
from http_mcp.security import SecurityValidator, SecurityConfig, create_default_validator


# 创建 FastMCP 实例
mcp = FastMCP("http-tool")


def load_config() -> dict:
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_security_validator() -> SecurityValidator:
    """获取安全验证器"""
    config = load_config()
    security_config = config.get('security', {})

    config_obj = SecurityConfig(
        allowed_domains=security_config.get('allowed_domains', ['*']),
        blocked_domains=security_config.get('blocked_domains', []),
        allow_private_ips=security_config.get('allow_private_ips', False),
        allow_http=security_config.get('allow_http', True),
        max_request_size=security_config.get('max_request_size', 10 * 1024 * 1024),
        max_response_size=security_config.get('max_response_size', 50 * 1024 * 1024),
        timeout=security_config.get('timeout', 30),
        verify_ssl=security_config.get('verify_ssl', True),
        allowed_methods=security_config.get('allowed_methods', ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
    )
    return SecurityValidator(config_obj)


def get_http_client() -> HTTPClient:
    """获取 HTTP 客户端"""
    config = load_config()
    http_config = config.get('http', {})

    # 获取代理设置
    proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy') or http_config.get('http_proxy', '')

    validator = get_security_validator()

    return HTTPClient(
        timeout=validator.config.timeout,
        verify_ssl=validator.config.verify_ssl,
        follow_redirects=False,
        http_proxy=proxy
    )


def strip_html_tags(html: str) -> str:
    """去除 HTML 标签"""
    # 移除 script 和 style 标签及其内容
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 移除 HTML 注释
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # 移除所有 HTML 标签
    html = re.sub(r'<[^>]+>', '', html)

    # 替换实体
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&amp;', '&')
    html = html.replace('&quot;', '"')
    html = html.replace('&#39;', "'")

    # 合并多余空白字符
    html = re.sub(r'\s+', ' ', html).strip()

    return html


def build_multipart_body(files: list) -> tuple:
    """
    构建 multipart/form-data 请求体

    Args:
        files: 文件/字段列表，每个元素为 dict，包含:
            - name: 表单字段名 (必需)
            - filename: 文件名 (仅文件字段需要)
            - content: 内容 (文件为内容，字段为值)
            - content_type: 文件类型 (仅文件字段需要，可选)

    Returns:
        tuple: (body, content_type, content_length)
    """
    import uuid

    # 生成 boundary
    boundary = uuid.uuid4().hex[:16]

    # 构建 body
    body_parts = []

    for file_info in files:
        name = file_info.get('name', 'file')
        filename = file_info.get('filename')
        content = file_info.get('content', '')
        content_type = file_info.get('content_type', 'application/octet-stream')

        # 每个部分
        body_parts.append(f'--{boundary}\r\n')

        # 根据是否有 filename 决定 Content-Disposition 格式
        if filename:
            body_parts.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n')
            body_parts.append(f'Content-Type: {content_type}\r\n')
        else:
            # 普通字段（无文件）
            body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n')

        body_parts.append('\r\n')
        body_parts.append(content)
        body_parts.append('\r\n')

    # 结束 boundary
    body_parts.append(f'--{boundary}--\r\n')

    body = ''.join(body_parts)
    content_type = f'multipart/form-data; boundary={boundary}'

    return body, content_type, len(body.encode('utf-8'))


@mcp.tool()
def http_send_request(
    content: str,
    baseurl: str,
    timeout: int = 30,
    strip_html: bool = True,
    allow_custom_host: bool = False,
    allow_custom_content_length: bool = False,
    files: list = None
) -> dict:
    """
    Send HTTP/1.1 requests with raw packet support (HTTP/2 not supported).

    Args:
        content: Raw HTTP request packet (including request line and headers).
            When using files parameter, content only needs basic request line and Host header.
            Example without files: 'GET /api/users HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n'
            Example with files: 'POST /upload HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n'
        baseurl: (Required) Full URL for the request (e.g., https://example.com).
            When using custom Host header, specify the actual server URL here.
        timeout: Request timeout in seconds, default: 30
        strip_html: Strip HTML tags from response body to reduce context size, default: true
        allow_custom_host: Allow custom Host header in request packet, default: false
        allow_custom_content_length: Allow custom Content-Length header in request packet, default: false

    Returns:
        dict: Response with status_code, headers, body, etc.
    """
    
        # --- FILE UPLOAD (RECOMMENDED) ---
        # files: List of files/fields for multipart/form-data upload.
        #     ⚠️  RECOMMENDED: Use this parameter for file upload instead of manually building multipart body!
        #     When this parameter is provided, the body will be automatically generated.

        #     content should be SIMPLE (only request line + Host):
        #     'POST /upload HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n'

        #     Each item is a dict:
        #     - name: Form field name (required)
        #     - filename: File name (required for file upload, omit for regular field)
        #     - content: File content or field value (required)
        #     - content_type: MIME type (optional, only for files)

        #     Example:
        #     [
        #         {"name": "file", "filename": "test.txt", "content": "hello world", "content_type": "text/plain"},
        #         {"name": "submit", "content": "upload"}  # regular field without filename
        #     ]

    if not content:
        return {"error": "content is required"}

    if not baseurl:
        return {"error": "baseurl is required (e.g., https://example.com)"}

    # 获取安全验证器和客户端
    security_validator = get_security_validator()
    client = get_http_client()

    try:
        # 解析请求
        parsed_request = HTTPRequestParser.parse(content)

        # 处理文件上传
        if files:
            # 构建 multipart body
            body, content_type, content_length = build_multipart_body(files)
            # 覆盖原始 body
            parsed_request.body = body
            # 移除原有的 Content-Type（会被自动覆盖）
            parsed_request.headers.pop('Content-Type', None)
            # 设置新的 Content-Type
            parsed_request.headers['Content-Type'] = content_type
            # HackRequests会自动计算Content-Length

        # baseurl 可以是简单的 "https" 或完整的 "https://a.com"
        # 如果包含 host，则使用其中的 host 作为实际连接地址
        actual_host = parsed_request.host  # 默认使用原始请求中的 host
        actual_scheme = baseurl

        if '://' in baseurl:
            # baseurl 是完整 URL，解析出实际的 host
            from urllib.parse import urlparse
            parsed_url = urlparse(baseurl)
            if parsed_url.hostname:
                actual_host = parsed_url.hostname
                actual_scheme = parsed_url.scheme
                # 如果有端口，也更新
                if parsed_url.port:
                    parsed_request.port = parsed_url.port

        # 安全检查 - 检查实际连接的域名
        error = security_validator.check_url_allowed(actual_scheme, actual_host)
        if error:
            return {"error": error, "blocked": True}

        # 安全检查 - 检查方法
        error = security_validator.validate_request(
            actual_host,
            parsed_request.method,
            parsed_request.body
        )
        if error:
            return {"error": error, "blocked": True}

        # 更新 parsed_request
        parsed_request.scheme = actual_scheme
        parsed_request.host = actual_host

        # 如果允许自定义 Host，使用原始请求头中的 Host 作为 HTTP 请求头
        custom_host = None
        if allow_custom_host and 'Host' in parsed_request.headers:
            custom_host = parsed_request.headers['Host']

        # 发送请求
        client.timeout = timeout
        start_time = time.perf_counter()
        response = client.send_request(
            parsed_request,
            strip_html=False,
            allow_custom_host=allow_custom_host,
            allow_custom_content_length=allow_custom_content_length,
            custom_host_header=custom_host
        )
        end_time = time.perf_counter()
        total_time = end_time - start_time
        # 处理 HTML 标签去除
        body = response.body
        html_stripped = False
        if strip_html:
            body = strip_html_tags(body)
            html_stripped = True

        # 检查响应大小
        error = security_validator.validate_response(body)
        if error:
            return {"error": error, "warning": True}
        if strip_html:
            return {
            "status_code": response.status_code,
            "reason": response.reason,      
            "headers": response.headers,
            "body": body,
            "body_length": len(body),
            "http_version": response.http_version,
            "html_stripped": html_stripped,
            "total_response_time_ms": round(total_time * 1000, 2)
        }
        else:
            # 返回结果
            return {
                "status_code": response.status_code,
                "reason": response.reason,      
                "headers": response.headers,
                "body": body,
                "body_length": len(body),
                "http_version": response.http_version,
                "raw_response": format_response(response),
                "html_stripped": html_stripped,
                "total_response_time_ms": round(total_time * 1000, 2)
            }

    except ValueError as e:
        return {"error": f"Parse error: {str(e)}"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}


@mcp.tool()
def http_build_request(
    method: str,
    url: str,
    headers: dict = None,
    body: str = None
) -> dict:
    """
    Build a raw HTTP request packet from method, URL, headers, and body.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
        url: Full URL (e.g., https://example.com/api/endpoint)
        headers: HTTP headers as key-value pairs
        body: Request body (optional)

    Returns:
        dict: Raw request packet and metadata
    """
    # IMPORTANT - multipart/form-data format:
    #     When using multipart/form-data, the boundary in Content-Type MUST match
    #     the boundary in the body. The body must follow this exact format:

    #     Content-Type: multipart/form-data; boundary=boundary123

    #     Body format (use \\r\\n for line breaks):
    #     --boundary123\\r\\n
    #     Content-Disposition: form-data; name="field_name"\\r\\n
    #     Content-Type: text/plain\\r\\n
    #     \\r\\n
    #     field_value\\r\\n
    #     --boundary123--\\r\\n

    #     Example:
    #     --boundary123\\r\\n
    #     Content-Disposition: form-data; name="file"; filename="test.txt"\\r\\n
    #     Content-Type: text/plain\\r\\n
    #     \\r\\n
    #     file content here\\r\\n
    #     --boundary123--\\r\\n
    if not url:
        return {"error": "url is required"}

    from urllib.parse import urlparse

    headers = headers or {}
    parsed_url = urlparse(url)

    # 构建 Host 头
    host = parsed_url.netloc
    if 'Host' not in headers:
        headers['Host'] = host

    # 构建请求
    path = parsed_url.path + ('?' + parsed_url.query if parsed_url.query else '')
    raw_request = HTTPRequestParser.build_raw_request(
        method=method,
        path=path,
        headers=headers,
        body=body
    )

    return {
        "raw_request": raw_request,
        "method": method,
        "url": url,
        "scheme": parsed_url.scheme
    }


def main():
    """主函数 - 运行 stdio 服务器"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
