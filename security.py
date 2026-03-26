"""
安全控制模块 - 提供请求安全检查
"""
import re
import ipaddress
from dataclasses import dataclass, field
from typing import List, Set, Optional
from urllib.parse import urlparse


@dataclass
class SecurityConfig:
    """安全配置"""
    # 允许的域名/主机列表（支持通配符）
    allowed_domains: List[str] = field(default_factory=lambda: ['*'])
    # 禁止的域名/主机列表
    blocked_domains: List[str] = field(default_factory=list)
    # 允许的 IP 地址列表
    allowed_ips: List[str] = field(default_factory=list)
    # 禁止的 IP 地址列表
    blocked_ips: List[str] = field(default_factory=list)
    # 最大请求体大小（字节）
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    # 最大响应体大小（字节）
    max_response_size: int = 50 * 1024 * 1024  # 50MB
    # 是否允许跟随重定向
    allow_redirects: bool = True
    # 是否允许不安全请求（如 HTTP）
    allow_http: bool = True  # 默认允许 HTTP
    # 是否允许内网 IP
    allow_private_ips: bool = False
    # 超时时间（秒）
    timeout: int = 30
    # 是否验证 SSL
    verify_ssl: bool = True
    # 允许的 HTTP 方法
    allowed_methods: List[str] = field(default_factory=lambda: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
    # 自定义阻止响应消息
    block_message: str = "Request blocked by security policy"


class SecurityValidator:
    """安全验证器"""

    def __init__(self, config: SecurityConfig = None):
        """
        初始化安全验证器

        Args:
            config: 安全配置
        """
        self.config = config or SecurityConfig()
        self._compile_patterns()

    def _compile_patterns(self):
        """编译域名模式"""
        self.allowed_patterns = []
        for pattern in self.config.allowed_domains:
            # 转换通配符为正则
            regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
            self.allowed_patterns.append(re.compile(f'^{regex_pattern}$'))

        self.blocked_patterns = []
        for pattern in self.config.blocked_domains:
            regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
            self.blocked_patterns.append(re.compile(f'^{regex_pattern}$'))

    def validate_request(self, host: str, method: str, body: Optional[str] = None) -> Optional[str]:
        """
        验证请求是否安全

        Args:
            host: 目标主机
            method: HTTP 方法
            body: 请求体

        Returns:
            str: 如果验证失败，返回错误消息；否则返回 None
        """
        # 检查方法
        if method not in self.config.allowed_methods:
            return f"HTTP method '{method}' is not allowed"

        # 检查请求体大小
        if body and len(body.encode('utf-8')) > self.config.max_request_size:
            return f"Request body too large (max {self.config.max_request_size} bytes)"

        # 检查协议
        # 这里只检查 host，不需要检查 schema，因为调用者会传入正确的 schema

        # 检查是否是内网 IP
        if not self.config.allow_private_ips:
            if self._is_private_ip(host):
                return f"Private IP addresses are not allowed: {host}"

        # 检查域名
        domain_check = self._validate_domain(host)
        if domain_check:
            return domain_check

        return None

    def validate_response(self, body: str) -> Optional[str]:
        """
        验证响应是否安全

        Args:
            body: 响应体

        Returns:
            str: 如果验证失败，返回错误消息；否则返回 None
        """
        if body and len(body.encode('utf-8')) > self.config.max_response_size:
            return f"Response body too large (max {self.config.max_response_size} bytes)"
        return None

    def _is_private_ip(self, host: str) -> bool:
        """检查是否是私有 IP"""
        try:
            # 尝试解析为 IP 地址
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_reserved
        except ValueError:
            # 不是有效的 IP 地址，可能是域名
            return False

    def _validate_domain(self, host: str) -> Optional[str]:
        """验证域名是否允许"""
        # 先检查是否在黑名单中
        for pattern in self.blocked_patterns:
            if pattern.match(host):
                return f"Domain '{host}' is blocked"

        # 检查是否在白名单中
        if '*' in self.config.allowed_domains:
            # 允许所有域名
            return None

        for pattern in self.allowed_patterns:
            if pattern.match(host):
                return None

        return f"Domain '{host}' is not in allowed list"

    def check_url_allowed(self, scheme: str, host: str) -> Optional[str]:
        """
        检查 URL 是否允许访问

        Args:
            scheme: 协议 (http/https)
            host: 主机

        Returns:
            str: 如果不允许，返回错误消息；否则返回 None
        """
        # 检查协议
        if scheme == 'http' and not self.config.allow_http:
            return "HTTP requests are not allowed, use HTTPS"

        # 验证域名
        return self._validate_domain(host)


def create_default_validator() -> SecurityValidator:
    """创建默认的安全验证器"""
    # 默认允许所有域名，但不允许私有 IP
    config = SecurityConfig(
        allowed_domains=['*'],
        allow_private_ips=False,
        max_request_size=10 * 1024 * 1024,
        max_response_size=50 * 1024 * 1024,
    )
    return SecurityValidator(config)


def create_strict_validator(allowed_domains: List[str]) -> SecurityValidator:
    """
    创建严格的安全验证器

    Args:
        allowed_domains: 允许的域名列表
    """
    config = SecurityConfig(
        allowed_domains=allowed_domains,
        allow_private_ips=False,
        allow_http=False,
        max_request_size=5 * 1024 * 1024,
        max_response_size=20 * 1024 * 1024,
    )
    return SecurityValidator(config)


def test_security():
    """测试安全验证器"""
    validator = create_default_validator()

    # 测试域名验证
    result = validator.validate_request('example.com', 'GET')
    print(f"example.com GET: {result}")

    result = validator.validate_request('evil.com', 'GET')
    print(f"evil.com GET: {result}")

    # 测试私有 IP
    result = validator.validate_request('192.168.1.1', 'GET')
    print(f"192.168.1.1 GET: {result}")

    # 测试方法
    result = validator.validate_request('example.com', 'CONNECT')
    print(f"example.com CONNECT: {result}")


if __name__ == '__main__':
    test_security()
