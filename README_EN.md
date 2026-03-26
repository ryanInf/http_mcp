# HTTP MCP - HTTP Request Tool
An MCP tool for sending HTTP/1.1 requests with built-in security controls.

Built on **FastMCP**.
Ideal for **web penetration testing** and **debugging**.

## Features
- Supports HTTP/1.1 (HTTP/2 not supported yet)
- Raw HTTP request message parsing
- **Security Controls**:
  - Domain whitelist/blacklist
  - Private IP access control
  - Request/response size limits
  - SSL certificate verification control
  - HTTP method restriction
- HTTP proxy support
- Automatic HTML tag stripping (shortens context, enabled by default)
- Custom Host header and Content-Length header support

## MCP Tools

### `http_send_request`
Sends a raw HTTP request message.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | string | Required | Raw HTTP request message |
| `baseurl` | string | Required | Full URL, e.g. `https://example.com` |
| `timeout` | number | 30 | Timeout in seconds |
| `strip_html` | boolean | true | Strip HTML tags from response |
| `allow_custom_host` | boolean | false | Allow custom Host header |
| `allow_custom_content_length` | boolean | false | Allow custom Content-Length header |
| `files` | array | - | ⚠️ **Recommended**: File upload, auto-builds valid `multipart/form-data` format |

**Raw Request Format:**
```
POST /api/users HTTP/1.1
Host: example.com
Content-Type: application/json
User-Agent: Mozilla/5.0

{"name": "test", "value": 123}
```

**Usage Examples:**

```python
# 1. Basic request
http_send_request(
    content="GET / HTTP/1.1\r\nHost: example.com\r\n\r\n",
    baseurl="https://example.com"
)

# 2. Specify target server
http_send_request(
    content="GET /api HTTP/1.1\r\nHost: example.com\r\n\r\n",
    baseurl="https://api.server.com"
)

# 3. Custom Host header (for CDN / virtual host testing)
http_send_request(
    content="GET / HTTP/1.1\r\nHost: custom-host.com\r\n\r\n",
    baseurl="https://example.com",
    allow_custom_host=True
)

# 4. Preserve HTML tags
http_send_request(
    content="GET /page HTTP/1.1\r\nHost: example.com\r\n\r\n",
    baseurl="https://example.com",
    strip_html=False
)

# 5. File upload (multipart/form-data)
# Note: content only needs request line + Host; no multipart body required
http_send_request(
    content="POST /upload HTTP/1.1\r\nHost: example.com\r\n\r\n",
    baseurl="https://example.com",
    files=[
        {"name": "file", "filename": "test.txt", "content": "hello world", "content_type": "text/plain"},
        {"name": "submit", "content": "upload"}  # Regular fields do not need filename
    ]
)
```

**Note:** When using `allow_custom_host=True`:
- `baseurl` defines the **actual server to connect to**
- The `Host` header uses the value from the raw request
- The target server may return an error if it does not recognize the custom Host header

---

### `http_build_request`
Builds a raw HTTP request message from method, URL, headers, and body.

**Parameters:**
- `method` (required): HTTP method
- `url` (required): Full URL
- `headers`: Request header object
- `body`: Request body

## Security Notes
⚠️ **Default Configuration Risks**:
- `allow_private_ips: true`: Private IP access is allowed by default. Risk of SSRF attacks in untrusted environments. Set to `false` in production.
- `verify_ssl: false`: SSL certificate verification is disabled by default. Risk of man-in-the-middle (MITM) attacks. Set to `true` in production.
- `follow_redirects: false`: Automatic redirect following is disabled by default. Enable manually if needed.
- `http_proxy: ""`: No proxy used by default.

**Proxy Priority**: Environment variables `HTTP_PROXY`/`HTTPS_PROXY` > `config.json` settings

## Configuration

### `config.json`
```json
{
  "security": {
    "allowed_domains": ["*"],
    "blocked_domains": [],
    "allow_private_ips": true,
    "allow_http": true,
    "max_request_size": 10485760,
    "max_response_size": 52428800,
    "timeout": 30,
    "verify_ssl": false,
    "allowed_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
  },
  "http": {
    "follow_redirects": false,
    "http_proxy": ""
  }
}
```

### HTTP Proxy Setup
Configure proxy via:
1. Modify `http.http_proxy` in `config.json`
2. Set environment variables `HTTP_PROXY` or `http_proxy` (**higher priority**)

### Environment Variables
- `HTTP_PROXY` / `http_proxy`: HTTP proxy address
- `HTTPS_PROXY` / `https_proxy`: HTTPS proxy address

## Installation
```bash
pip install -r requirements.txt
```

**Dependencies**:
- fastmcp >= 0.1.0
- hackrequests >= 0.2.0
- beautifulsoup4 >= 4.12.0

## Testing
```bash
# Run from project root
PYTHONPATH=. python3 http_mcp/test_mcp.py
```

## MCP Configuration
Add to your `.mcp.json` file. Replace `<YOUR_PROJECT_ROOT_PATH>` with your actual code directory.

```json
{
  "mcpServers": {
    "http-tool": {
      "command": "python3",
      "args": ["<YOUR_PROJECT_ROOT_PATH>/http_mcp/run_server.py"]
    }
  }
}
```

Or using **uv**:
```json
{
  "mcpServers": {
    "http-tool": {
      "command": "uv",
      "args": ["run", "python3", "<YOUR_PROJECT_ROOT_PATH>/http_mcp/run_server.py"]
    }
  }
}
```

## Test Status
| Test Item | Status |
|-----------|--------|
| GET Request | ✅ Pass |
| POST JSON | ✅ Pass |
| POST form-urlencoded | ✅ Pass |
| Custom Headers | ✅ Pass |
| Status Codes 200/404/500 | ✅ Pass |
| Delayed Response (delay/N) | ✅ Pass |
| PUT/PATCH/DELETE | ✅ Pass |
| OPTIONS Request | ✅ Pass |
| Query String Params | ✅ Pass |
| Redirect Response (no follow) | ✅ Pass |
| Empty Body POST | ✅ Pass |
| UTF-8 Chinese Characters | ✅ Pass |
| HTTP-MCP/1.0 Default User-Agent | ✅ Pass |

Tested and compatible with major LLMs: MiniMax-M2.5/2.7, doubao-seed-2.0-pro, Kimi k2.5, etc.

## Known Bugs (Will Not Fix)
🐛 Bug #1: Empty header values cause errors (native HackRequests.py bug)
🐛 Bug #2: Chunked Transfer-Encoding not supported

## Usage
![Usage](assets/image1.png)

## Demo
![Demo](assets/image.png)

## Security Best Practices
1. **Always modify default security settings in production**:
   - Set `allow_private_ips: false` to block intranet access
   - Set `verify_ssl: true` to enable SSL certificate validation
2. Restrict `allowed_domains` to only required target domains
3. Do not expose MCP service ports in public environments
4. Regularly update dependencies to patch security vulnerabilities

## License
MIT