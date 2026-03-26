#!/usr/bin/env python3
"""
HTTP MCP Server Launcher
"""
import os
import sys

# Add project to path
sys.path.insert(0, 'your project path')

# Set up environment
os.environ['PYTHONPATH'] = '.'
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:8080'

# Import and run server
from http_mcp.server import main
sys.exit(main())
