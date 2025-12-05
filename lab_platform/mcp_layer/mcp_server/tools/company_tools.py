from __future__ import annotations

from pathlib import Path
import json
from typing import Dict, Any, List

DATA_PATH = Path(__file__).parent / "company_info.json"


def _load_data() -> Dict[str, Any]:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))

    # Simple starter dataset – safe defaults for the lab
    return {
        "policies": {
            "onboarding": "All new employees complete security training in first 30 days.",
        },
        "policy_framework_mappings": {
            "POL-HIPAA-AC-01": {
                "HIPAA": [
                    "HIPAA 164.312(a)(1) – Access Control",
                    "HIPAA 164.308(a)(4) – Information Access Management",
                ]
            }
        },
        # Now keyed by clinic_id → department → workflow
        "clinic_workflows": {
            "clinic_01": {
                "Cardiology": (
                    "Verify history → vitals → cardiologist consult → "
                    "follow-up scheduling."
                )
            }
        },
        "allowed_actions": {
            "Physician": ["view_clinical_docs", "order_tests", "update_notes"],
            "Employee": ["view_company_policies"],
        },
    }


# ---------------------------------------------------------
# Existing tools (slightly upgraded)
# ---------------------------------------------------------
def company_lookup_policy(policy_name: str) -> str | None:
    data = _load_data()
    return data.get("policies", {}).get(policy_name)


def company_get_clinic_workflow(
    clinic_id: str,
    department: str,
    **_: Any,
) -> Dict[str, Any]:
    """
    Updated to match your MCP input payload:

      "input": {
        "clinic_id": "clinic_01",
        "department": "Cardiology"
      }

    We return a structured object (better for JSON / UI).
    """
    data = _load_data()
    workflows = data.get("clinic_workflows", {})

    dept_map = workflows.get(clinic_id, {})
    # Be tolerant of exact / case variants
    workflow = (
        dept_map.get(department)
        or dept_map.get(department.lower())
        or "No workflow found for this clinic/department."
    )

    return {
        "clinic_id": clinic_id,
        "department": department,
        "workflow": workflow,
    }


def company_list_allowed_actions(role: str) -> List[str]:
    data = _load_data()
    return data.get("allowed_actions", {}).get(role, [])


# ---------------------------------------------------------
# New tools used in Phase 5
# ---------------------------------------------------------
def restrict_bucket_policy(
    storage_account_name: str,
    container_name: str,
    policy_level: str,
    requested_by: str,
    **_: Any,
) -> Dict[str, Any]:
    """
    Simulated bucket hardening tool.

    Matches input payload:

      "input": {
        "storage_account_name": "ragmcpevidence001",
        "container_name": "docs-raw",
        "policy_level": "deny_public_access",
        "requested_by": "devsec-999"
      }
    """
    return {
        "action": "restrict_bucket_policy",
        "storage_account_name": storage_account_name,
        "container_name": container_name,
        "policy_level": policy_level,
        "requested_by": requested_by,
        "status": "simulated_change_applied",
    }


def grc_map_policy_to_framework(
    policy_id: str,
    framework: str,
    **_: Any,
) -> Dict[str, Any]:
    """
    Map an internal policy ID to one or more framework controls.

    Matches input payload:

      "input": {
        "policy_id": "POL-HIPAA-AC-01",
        "framework": "HIPAA"
      }
    """
    data = _load_data()

    mappings = (
        data.get("policy_framework_mappings", {})
        .get(policy_id, {})
        .get(framework, [])
    )

    return {
        "policy_id": policy_id,
        "framework": framework,
        "mappings": mappings,
        "found": bool(mappings),
    }


def grc_map_policy_to_framework(
    policy_id: str,
    framework: str,
    **_: Any,
) -> Dict[str, Any]:
    """
    Map an internal policy ID to one or more framework controls.

    Matches input payload:

      "input": {
        "policy_id": "POL-HIPAA-AC-01",
        "framework": "HIPAA"
      }
    """
    data = _load_data()

    mappings = (
        data.get("policy_framework_mappings", {})
        .get(policy_id, {})
        .get(framework, [])
    )

    return {
        "policy_id": policy_id,
        "framework": framework,
        "mappings": mappings,
        "found": bool(mappings),
    }
