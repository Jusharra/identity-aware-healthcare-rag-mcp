# platform/mcp_layer/mcp_server/server.py

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"


@dataclass
class Tool:
    name: str
    handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
    allowed_requester_roles: List[str]
    config: Dict[str, Any]


class MCPServer:
    """
    Minimal MCP runtime for this lab:

    - Loads tools and RBAC from config.yaml
    - Enforces per-tool allowed_requester_roles
    - Logs every invocation to JSONL as evidence
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self.tools: Dict[str, Tool] = {}
        self.log_path: Path = BASE_DIR / "logs" / "access.log.jsonl"

        self._load_config()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> None:
        with self.config_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        tools_cfg: Dict[str, Dict[str, Any]] = cfg.get("tools", {})
        self.tools.clear()

        # Optional log path override from config
        logging_cfg = cfg.get("logging", {})
        log_file = logging_cfg.get("file")
        if log_file:
            self.log_path = (BASE_DIR / log_file).resolve()
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

        for tool_name, t_cfg in tools_cfg.items():
            module_name = t_cfg["module"]
            func_name = t_cfg["function"]

            module = importlib.import_module(module_name)
            handler = getattr(module, func_name)

            allowed_roles = t_cfg.get("allowed_requester_roles", []) or []

            self.tools[tool_name] = Tool(
                name=tool_name,
                handler=handler,
                allowed_requester_roles=allowed_roles,
                config=t_cfg,
            )

    def run_tool(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        caller: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Unknown tool
        if tool_name not in self.tools:
            result = {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }
            self._log(tool_name, input_data, caller, result, allowed=False)
            return result

        tool = self.tools[tool_name]

        # Simple RBAC gate based on caller.role
        caller_role = caller.get("role")
        if tool.allowed_requester_roles and caller_role not in tool.allowed_requester_roles:
            result = {
                "success": False,
                "error": f"Role {caller_role} not allowed to run {tool_name}",
            }
            self._log(tool_name, input_data, caller, result, allowed=False)
            return result

        context = {
            "caller": caller,
            "tool_config": tool.config,
        }

        try:
            output = tool.handler(input_data, context)
            # Normalize success flag
            if "success" not in output:
                output = {"success": True, **output}
            result = output
            self._log(tool_name, input_data, caller, result, allowed=True)
            return result
        except Exception as exc:  # we log and return error, no crash
            result = {
                "success": False,
                "error": str(exc),
            }
            self._log(tool_name, input_data, caller, result, allowed=True)
            return result

    def _log(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        caller: Dict[str, Any],
        result: Dict[str, Any],
        allowed: bool,
    ) -> None:
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "tool": tool_name,
            "caller": caller,
            "input": input_data,
            "result": result,
            "allowed": allowed,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    # Manual smoke test entrypoint
    server = MCPServer()
    demo = server.run_tool(
        "echo",
        {"message": "Hello from MCP"},
        {"id": "demo.user", "role": "Demo"},
    )
    print(json.dumps(demo, indent=2))
