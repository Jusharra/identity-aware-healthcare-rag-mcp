# tests/test_mcp_basic.py

import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab_platform.mcp_layer.mcp_server import MCPServer # <— use alias package


def test_echo_tool_happy_path():
    server = MCPServer()
    caller = {"id": "demo.user", "role": "Demo"}
    input_data = {"message": "Test 123"}

    result = server.run_tool("echo", input_data, caller)

    assert result["success"] is True
    assert result["echo"]["message"] == "Test 123"
    assert result["metadata"]["caller_id"] == "demo.user"
    assert result["metadata"]["caller_role"] == "Demo"


def test_unknown_tool_returns_error():
    server = MCPServer()
    caller = {"id": "demo.user", "role": "Demo"}

    result = server.run_tool("does_not_exist", {}, caller)

    assert result["success"] is False
    assert "Unknown tool" in result["error"]
