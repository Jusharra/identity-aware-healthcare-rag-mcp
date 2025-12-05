import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from functools import lru_cache
import yaml


class PolicyEngine:
    """
    Tiny RBAC + ABAC evaluator for the Identity Gateway.

    - RBAC: which RAG scopes + MCP tools a role can access
    - ABAC: attribute-based checks evaluated per request
    """

    def __init__(self, config_path: str | None = None) -> None:
        if config_path is None:
            # default to abac_policies.yaml next to this file
            base_dir = Path(__file__).resolve().parent / "config"
            config_path = base_dir / "abac_policies.yaml"

        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Policy config not found at {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def roles(self) -> Dict[str, Any]:
        return self._config.get("roles", {})

    @property
    def abac_rules(self) -> List[Dict[str, Any]]:
        return self._config.get("abac_rules", [])

    # ---------- RAG access helpers ----------

    def get_rag_scopes_for_role(self, role: str) -> List[str]:
        role_cfg = self.roles.get(role, {})
        return role_cfg.get("rag_access", []) or []

    # ---------- MCP access helpers ----------

    def is_tool_allowed_for_role(self, role: str, tool_name: str) -> bool:
        role_cfg = self.roles.get(role, {})
        tools = role_cfg.get("mcp_tools", []) or []
        if "*" in tools:
            return True
        return tool_name in tools

    # ---------- ABAC evaluation ----------

    def evaluate_abac_for_doc(
        self,
        claims: Dict[str, Any],
        doc: Dict[str, Any],
        scope: str,
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate ABAC rules for a given doc and target scope.

        Returns:
            allowed: bool
            reasons: list of strings describing denials or passes
        """
        reasons: List[str] = []
        allowed = True

        for rule in self.abac_rules:
            applies_to = rule.get("applies_to")
            if applies_to and scope not in applies_to:
                continue

            condition_expr = rule.get("condition")
            local_ctx = {"claims": claims, "doc": doc}

            try:
                result = bool(eval(condition_expr, {"__builtins__": {}}, local_ctx))
            except Exception as exc:  # noqa: BLE001
                reasons.append(f"Rule {rule.get('name')} error: {exc}")
                # fail-safe: deny on evaluation errors
                allowed = False
                continue

            if not result:
                deny_tags = rule.get("deny_when_false", [])
                reasons.append(
                    f"Rule {rule.get('name')} failed; deny tags: {deny_tags}"
                )
                allowed = False

        return allowed, reasons

    def evaluate_tool_abac(
        self,
        claims: Dict[str, Any],
        tool_name: str,
    ) -> Tuple[bool, List[str]]:
        """
        Hook for tool-level ABAC rules if you want them later.
        For now, we simply allow if role-based tool access is granted
        and license_status is valid.
        """
        reasons: List[str] = []
        role = claims.get("role")
        if not role:
            return False, ["Missing role in claims"]

        if not self.is_tool_allowed_for_role(role, tool_name):
            return False, [f"Tool {tool_name} not allowed for role {role}"]

        # Example ABAC: license must be valid for sensitive tools
        if tool_name.startswith("identity_") and claims.get("license_status") != "valid":
            reasons.append("license_status not valid for identity tools")
            return False, reasons

        return True, reasons
# --- MCP Tool Policy Loading --- #

_MCP_TOOL_POLICIES_CACHE: Dict[str, Any] | None = None

MCP_TOOL_POLICIES_PATH = (
    Path(__file__).parent / "config" / "mcp_tool_policies.yaml"
)

def _get_mcp_policy_path() -> str:
    """
    Returns the path to mcp_tool_policies.yaml under identity_gateway/config.
    """
    base_dir = os.path.dirname(__file__)
    return os.path.join(base_dir, "config", "mcp_tool_policies.yaml")


# Base dir: lab_platform/identity_gateway/
BASE_DIR = os.path.dirname(__file__)

# config/ under identity_gateway
POLICY_DIR = os.path.join(BASE_DIR, "config")

MCP_POLICY_FILE = os.path.join(POLICY_DIR, "mcp_tool_policies.yaml")


@lru_cache(maxsize=1)
def load_mcp_tool_policies() -> dict:
    """Load MCP tool policies from YAML once and cache in memory."""
    if not os.path.exists(MCP_POLICY_FILE):
        return {}

    with open(MCP_POLICY_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Normalize structure a bit
    return data


def is_tool_allowed(role: str, tool_name: str) -> bool:
    """
    Return True if `role` is allowed to execute `tool_name`
    according to config/mcp_tool_policies.yaml
    """
    policies = load_mcp_tool_policies()
    roles_cfg = policies.get("roles", {})
    role_cfg = roles_cfg.get(role)
    if not role_cfg:
        return False

    allowed = role_cfg.get("allowed_tools", [])
    if not allowed:
        return False

    # wildcard: IT_Admin, etc.
    if "*" in allowed:
        return True

    return tool_name in allowed

