#!/usr/bin/env python

"""
Generate evidence bundle for the RAG + MCP governance lab.

What this does (for auditors / CISOs):
1. Reads JSONL logs for:
   - identity_events.jsonl  (who accessed what)
   - mcp_tool_events.jsonl  (who called which MCP tools, allowed/denied)
2. Writes:
   - platform/evidence/access_events.csv
   - platform/evidence/mcp_tool_events.csv
   - platform/evidence/summary.json
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# -----------------------------
# Paths
# -----------------------------
SCRIPT_DIR = Path(__file__).resolve().parent  # .../platform/devsecops/scripts
PLATFORM_DIR = SCRIPT_DIR.parents[2]          # .../platform
LOGS_DIR = PLATFORM_DIR / "logs"
EVIDENCE_DIR = PLATFORM_DIR / "evidence"

IDENTITY_LOG = LOGS_DIR / "identity_events.jsonl"
MCP_LOG = LOGS_DIR / "mcp_tool_events.jsonl"

ACCESS_CSV = EVIDENCE_DIR / "access_events.csv"
MCP_CSV = EVIDENCE_DIR / "mcp_tool_events.csv"
SUMMARY_JSON = EVIDENCE_DIR / "summary.json"


def load_jsonl(path: Path):
    """Best-effort load of JSONL file. Returns list of dicts."""
    if not path.exists():
        print(f"[evidence] ⚠️ Log file not found, skipping: {path}", file=sys.stderr)
        return []

    events = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                print(
                    f"[evidence] ⚠️ Skipping invalid JSON on {path.name}:{line_no}",
                    file=sys.stderr,
                )
    return events


def ensure_dirs():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)  # in case you want to drop logs locally


def write_access_csv(identity_events):
    """Flatten identity events to CSV for auditors."""
    if not identity_events:
        # still create an empty CSV with headers so artifacts are predictable
        headers = [
            "timestamp",
            "actor_id",
            "actor_role",
            "department",
            "resource",
            "action",
            "decision",
            "reason",
        ]
        with ACCESS_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        return

    rows = []
    for ev in identity_events:
        caller = ev.get("caller_claims", {})
        rows.append(
            {
                "timestamp": ev.get("timestamp"),
                "actor_id": caller.get("sub"),
                "actor_role": caller.get("role"),
                "department": caller.get("department"),
                "resource": ev.get("resource") or ev.get("target_resource"),
                "action": ev.get("action") or ev.get("operation"),
                "decision": ev.get("decision", "unknown"),
                "reason": ev.get("reason", ""),
            }
        )

    headers = [
        "timestamp",
        "actor_id",
        "actor_role",
        "department",
        "resource",
        "action",
        "decision",
        "reason",
    ]
    with ACCESS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_mcp_csv(mcp_events):
    """Flatten MCP tool invocations to CSV."""
    if not mcp_events:
        headers = [
            "timestamp",
            "actor_id",
            "actor_role",
            "tool_name",
            "decision",
            "justification",
            "ticket_id",
        ]
        with MCP_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        return

    rows = []
    for ev in mcp_events:
        caller = ev.get("caller_claims", {})
        rows.append(
            {
                "timestamp": ev.get("timestamp"),
                "actor_id": caller.get("sub"),
                "actor_role": caller.get("role"),
                "tool_name": ev.get("tool_name") or ev.get("tool"),
                "decision": ev.get("decision", "unknown"),
                "justification": ev.get("justification", ""),
                "ticket_id": ev.get("ticket_id", ""),
            }
        )

    headers = [
        "timestamp",
        "actor_id",
        "actor_role",
        "tool_name",
        "decision",
        "justification",
        "ticket_id",
    ]
    with MCP_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(identity_events, mcp_events):
    """Aggregate into a compact JSON summary."""

    # -------- Identity access stats --------
    access_decisions = Counter()
    access_by_role = defaultdict(lambda: Counter())
    access_by_resource = defaultdict(lambda: Counter())

    for ev in identity_events:
        decision = ev.get("decision", "unknown")
        caller = ev.get("caller_claims", {})
        role = caller.get("role", "unknown")
        resource = ev.get("resource") or ev.get("target_resource") or "unknown"

        access_decisions[decision] += 1
        access_by_role[role][decision] += 1
        access_by_resource[resource][decision] += 1

    # -------- MCP tool usage stats --------
    tool_decisions = Counter()
    tool_by_role = defaultdict(lambda: Counter())
    privileged_tool_usage = Counter()

    PRIVILEGED_TOOLS = {
      "restrict_bucket_policy",
      "update_storage_network_rules",
      "rotate_encryption_key",
      "disable_public_access",
    }

    for ev in mcp_events:
        decision = ev.get("decision", "unknown")
        tool = ev.get("tool_name") or ev.get("tool") or "unknown"
        caller = ev.get("caller_claims", {})
        role = caller.get("role", "unknown")

        tool_decisions[decision] += 1
        tool_by_role[role][tool] += 1

        if tool in PRIVILEGED_TOOLS:
            privileged_tool_usage[tool] += 1

    # -------- Light GRC mapping --------
    # This is deliberately high-level and illustrative, not a full catalog.
    grc_mapping = {
        "HIPAA": {
            "access_logging": [
                "164.312(b) - Audit controls",
                "164.308(a)(1) - Security management process",
            ],
            "privileged_access": [
                "164.308(a)(3) - Workforce security",
            ],
        },
        "ISO27001": {
            "access_logging": [
                "A.5.15 - Logging",
                "A.8.16 - Monitoring activities",
            ],
            "privileged_access": [
                "A.5.18 - Access rights",
            ],
        },
        "ISO42001": {
            "ai_governance": [
                "8.2.2 - AI system access control",
                "8.2.3 - Traceability and logging for AI",
            ],
            "tool_governance": [
                "8.3.4 - Technical controls for AI functions",
            ],
        },
    }

    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "identity_events": {
            "total_events": sum(access_decisions.values()),
            "decisions": access_decisions,
            "by_role": {role: dict(counts) for role, counts in access_by_role.items()},
            "by_resource": {
                res: dict(counts) for res, counts in access_by_resource.items()
            },
        },
        "mcp_tool_events": {
            "total_events": sum(tool_decisions.values()),
            "decisions": tool_decisions,
            "by_role": {role: dict(tools) for role, tools in tool_by_role.items()},
            "privileged_tool_usage": dict(privileged_tool_usage),
        },
        "grc_mapping": grc_mapping,
    }

    # Convert Counters to plain dicts for JSON
    def _normalize(obj):
        if isinstance(obj, Counter):
            return dict(obj)
        if isinstance(obj, dict):
            return {k: _normalize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_normalize(v) for v in obj]
        return obj

    return _normalize(summary)


def main():
    print("[evidence] 📁 Ensuring evidence directories exist...")
    ensure_dirs()

    print(f"[evidence] 📥 Loading identity events from: {IDENTITY_LOG}")
    identity_events = load_jsonl(IDENTITY_LOG)

    print(f"[evidence] 📥 Loading MCP tool events from: {MCP_LOG}")
    mcp_events = load_jsonl(MCP_LOG)

    print(f"[evidence] 📄 Writing access events CSV → {ACCESS_CSV}")
    write_access_csv(identity_events)

    print(f"[evidence] 📄 Writing MCP tool events CSV → {MCP_CSV}")
    write_mcp_csv(mcp_events)

    print(f"[evidence] 📊 Building summary JSON → {SUMMARY_JSON}")
    summary = build_summary(identity_events, mcp_events)
    with SUMMARY_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("[evidence] ✅ Evidence bundle generated.")


if __name__ == "__main__":
    main()
