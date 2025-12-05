
# lab_platform/mcp_layer/mcp_server/__init__.py

from __future__ import annotations

from typing import Any, Dict, Callable

from lab_platform.identity_gateway.policy_engine import is_tool_allowed
from lab_platform.rag_layer.orchestrator import RAGOrchestrator
from lab_platform.mcp_layer.mcp_server.tools import iam_tools, company_tools
from lab_platform.identity_gateway import policy_engine




ToolFunc = Callable[..., Any]


class MCPServer:
    """
    Minimal MCP runtime:

    - Registers IAM tools and RAG bridge
    - Enforces tool-level policies (role -> allowed_tools)
    - Wraps results in a consistent response envelope
    """

    def __init__(self) -> None:
        # Existing tools...
        self.tools = {
            # Company-info tools
            "company_lookup_policy": company_tools.company_lookup_policy,
            "company_get_clinic_workflow": company_tools.company_get_clinic_workflow,
            "company_list_allowed_actions": company_tools.company_list_allowed_actions,

            # IAM tools
            "identity_create_demo_user": iam_tools.identity_create_demo_user,
            "identity_check_user_role": iam_tools.identity_check_user_role,
            "identity_check_MFA_config": iam_tools.identity_check_MFA_config,
            "identity_list_user_permissions": iam_tools.identity_list_user_permissions,
            "identity_assign_role": iam_tools.identity_assign_role,
            "identity_disable_user": iam_tools.identity_disable_user,
            "grant_temp_admin": iam_tools.grant_temp_admin,

            # GRC / DevSecOps tools
            "restrict_bucket_policy": company_tools.restrict_bucket_policy,
            "grc_lookup_control": iam_tools.grc_lookup_control,
            "grc_map_policy_to_framework": company_tools.grc_map_policy_to_framework,

            # Already existing RAG bridge
            "rag_query": self._rag_query_wrapper,
        }

    def _rag_query_wrapper(
        self,
        input_data: Dict[str, Any],
        caller_claims: Dict[str, Any],
    ) -> Dict[str, Any]:
        query_text = input_data.get("query_text", "")
        requested_scope = input_data.get("requested_scope", "")

        return self._rag_orchestrator.query(
            query_text=query_text,
            claims=caller_claims,
            requested_scope=requested_scope,
        )

    def run_tool(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        caller_claims: Dict[str, Any],
    ) -> Dict[str, Any]:
        role = caller_claims.get("role", "Unknown")

        # 1) Policy gate: is this tool even allowed for this role?
        if not is_tool_allowed(role, tool_name):
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not allowed for role '{role}'",
            }

        func = self.tools.get(tool_name)
        if not func:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }

        try:
            # Route based on tool type
            if tool_name == "identity_create_demo_user":
                result = func(
                    user_id=input_data["user_id"],
                    role=input_data["role"],
                    mfa_enabled=bool(input_data.get("mfa_enabled", True)),
                )
            elif tool_name in ("identity_check_user_role", "identity_check_MFA_config"):
                result = func(user_id=input_data["user_id"])
            elif tool_name == "rag_query":
                result = func(input_data, caller_claims)
            else:
                # Generic fallback if you add future tools that accept kwargs
                result = func(**input_data)

            return {
                "success": True,
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": f"Tool '{tool_name}' failed: {exc}",
            }

