# lab_platform/mcp_layer/iam_tools.py

from __future__ import annotations

import json
from typing import List, Dict, Any
from pathlib import Path
from typing import Any, Dict

DB_PATH = Path(__file__).parent / "iam_state.json"


def _load_db() -> Dict[str, Any]:
    if DB_PATH.exists():
        return json.loads(DB_PATH.read_text(encoding="utf-8"))
    return {"users": {}}


def _save_db(db: Dict[str, Any]) -> None:
    DB_PATH.write_text(json.dumps(db, indent=2), encoding="utf-8")


def identity_check_user_role(user_id: str) -> str | None:
    db = _load_db()
    user = db["users"].get(user_id)
    if not user:
        return None
    return user.get("role")


def identity_check_MFA_config(user_id: str) -> bool:
    db = _load_db()
    user = db["users"].get(user_id)
    if not user:
        return False
    return bool(user.get("mfa_enabled", False))


def identity_create_demo_user(user_id: str, role: str, mfa_enabled: bool = True) -> bool:
    """
    Simple local 'directory' for lab purposes.
    """
    db = _load_db()
    db["users"][user_id] = {
        "role": role,
        "mfa_enabled": mfa_enabled,
        "disabled": False,
        "permissions": [],  # can be filled by identity_assign_role
        "temp_admin_until": None,
    }
    _save_db(db)
    return True

def identity_list_user_permissions(user_id: str) -> List[str]:
    """
    Return the permissions array for a user.
    """
    db = _load_db()
    user = db["users"].get(user_id)
    if not user:
        return []
    return user.get("permissions", [])


def identity_assign_role(user_id: str, role: str, permissions: List[str] | None = None) -> bool:
    """
    Update a user's role and optional permissions list.
    """
    db = _load_db()
    user = db["users"].get(user_id)
    if not user:
        user = {}
        db["users"][user_id] = user

    user["role"] = role
    if permissions is not None:
        user["permissions"] = permissions

    _save_db(db)
    return True


def identity_disable_user(user_id: str) -> bool:
    """
    Mark user as disabled (soft-delete / account lock for the lab).
    """
    db = _load_db()
    user = db["users"].get(user_id)
    if not user:
        return False
    user["disabled"] = True
    _save_db(db)
    return True


def grant_temp_admin(user_id: str, until_iso: str) -> bool:
    """
    Grant temporary admin, e.g. until a given ISO-8601 timestamp.
    (Lab only – no real time validation here.)
    """
    db = _load_db()
    user = db["users"].get(user_id)
    if not user:
        return False

    perms = set(user.get("permissions", []))
    perms.add("admin")
    user["permissions"] = sorted(perms)
    user["temp_admin_until"] = until_iso

    _save_db(db)
    return True


# --------------------
# GRC / DevSecOps tools
# --------------------


def restrict_bucket_policy(bucket_name: str, reason: str) -> Dict[str, Any]:
    """
    Lab stub: pretend we restricted an S3/Blob bucket policy.
    In reality you'd call Azure APIs or Terraform pipelines.
    """
    # This just returns a structured record that can be logged as evidence.
    return {
        "bucket_name": bucket_name,
        "action": "restrict_policy",
        "status": "requested",
        "reason": reason,
    }


def grc_lookup_control(control_id: str) -> Dict[str, Any]:
    """
    Lab stub: pretend to look up a control from your GRC catalog.
    For now we just echo the ID + fake mapping context.
    """
    # Later you can wire this into your RAG/GRC index.
    return {
        "control_id": control_id,
        "framework": "ISO-27001",
        "section": "A.9 Access Control",
        "description": "Stubbed control lookup for lab.",
    }


def grc_map_policy_to_framework(policy_name: str) -> Dict[str, Any]:
    """
    Lab stub to show mapping between internal policy and frameworks.
    """
    return {
        "policy_name": policy_name,
        "mapped_frameworks": [
            {"framework": "ISO-27001", "section": "A.12 Operations Security"},
            {"framework": "ISO-42001", "section": "6.3 AI System Controls"},
        ],
    }   
