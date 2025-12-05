# platform/mcp_layer/mcp_server/tools/echo.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def run(input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple MCP tool used for smoke testing the MCP runtime.

    Input example:
      {
        "message": "Hello from client",
        "extra": {"foo": "bar"}
      }
    """
    caller = context.get("caller", {})
    return {
        "success": True,
        "echo": input,
        "metadata": {
            "received_at": datetime.utcnow().isoformat() + "Z",
            "caller_id": caller.get("id"),
            "caller_role": caller.get("role"),
        },
    }
