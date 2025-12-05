from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from lab_platform.identity_gateway.policy_engine import PolicyEngine

app = FastAPI(title="Identity Gateway – RAG + MCP")

policy_engine = PolicyEngine()


class ClaimsModel(BaseModel):
    # minimal claims for the lab – mimic Entra ID custom claims
    sub: str
    role: str
    department: str | None = None
    clinic_id: str | None = None
    clearance: str | None = None
    license_status: str | None = None
    region: str | None = None


class RagRequest(BaseModel):
    claims: ClaimsModel
    requested_scope: str  # e.g. "clinical_all", "clinical_department"
    doc_metadata: Dict[str, Any]  # e.g. {"department": "Cardiology", "clinic_id": "clinic_01"}


class RagDecisionResponse(BaseModel):
    allowed: bool
    rag_scopes: list[str]
    reasons: list[str]
    evidence_record_id: str | None = None


class McpRequest(BaseModel):
    claims: ClaimsModel
    tool_name: str
    tool_args: Dict[str, Any] = {}


class McpDecisionResponse(BaseModel):
    allowed: bool
    reasons: list[str]
    evidence_record_id: str | None = None


def _log_evidence(event_type: str, payload: Dict[str, Any]) -> str:
    """
    For now: log to stdout in a structured way.

    Later: push to Azure Blob ('logs' container) and Log Analytics.
    Returns a fake evidence_record_id for traceability.
    """
    evidence_id = f"ev-{int(datetime.now(tz=timezone.utc).timestamp())}"
    log_entry = {
      "evidence_id": evidence_id,
      "event_type": event_type,
      "timestamp": datetime.now(tz=timezone.utc).isoformat(),
      **payload,
    }
    print(f"[EVIDENCE] {log_entry}")
    return evidence_id


@app.post("/gateway/rag", response_model=RagDecisionResponse)
async def rag_decision(
    req: RagRequest,
    x_request_id: str | None = Header(default=None),
):
    claims_dict = req.claims.model_dump()
    role = claims_dict.get("role")

    # RBAC scopes for this role
    allowed_scopes = policy_engine.get_rag_scopes_for_role(role)
    reasons: list[str] = []

    if req.requested_scope not in allowed_scopes:
        reasons.append(
            f"Requested scope {req.requested_scope} not in role {role} RAG scopes {allowed_scopes}"
        )
        evidence_id = _log_evidence(
            "rag_access_denied",
            {
                "role": role,
                "claims": claims_dict,
                "requested_scope": req.requested_scope,
                "doc_metadata": req.doc_metadata,
                "reasons": reasons,
                "request_id": x_request_id,
            },
        )
        return RagDecisionResponse(
            allowed=False,
            rag_scopes=allowed_scopes,
            reasons=reasons,
            evidence_record_id=evidence_id,
        )

    # ABAC evaluation for this document + scope
    abac_allowed, abac_reasons = policy_engine.evaluate_abac_for_doc(
        claims=claims_dict,
        doc=req.doc_metadata,
        scope=req.requested_scope,
    )
    reasons.extend(abac_reasons)

    event_type = "rag_access_allowed" if abac_allowed else "rag_access_denied"
    evidence_id = _log_evidence(
        event_type,
        {
            "role": role,
            "claims": claims_dict,
            "requested_scope": req.requested_scope,
            "doc_metadata": req.doc_metadata,
            "reasons": reasons,
            "request_id": x_request_id,
        },
    )

    return RagDecisionResponse(
        allowed=abac_allowed,
        rag_scopes=allowed_scopes,
        reasons=reasons,
        evidence_record_id=evidence_id,
    )


@app.post("/gateway/mcp", response_model=McpDecisionResponse)
async def mcp_decision(
    req: McpRequest,
    x_request_id: str | None = Header(default=None),
):
    claims_dict = req.claims.model_dump()
    role = claims_dict.get("role")

    # RBAC + simple ABAC for tools
    allowed, reasons = policy_engine.evaluate_tool_abac(
        claims=claims_dict,
        tool_name=req.tool_name,
    )

    event_type = "mcp_tool_allowed" if allowed else "mcp_tool_denied"
    evidence_id = _log_evidence(
        event_type,
        {
            "role": role,
            "claims": claims_dict,
            "tool_name": req.tool_name,
            "tool_args": req.tool_args,
            "reasons": reasons,
            "request_id": x_request_id,
        },
    )

    if not allowed:
        return McpDecisionResponse(
            allowed=False,
            reasons=reasons,
            evidence_record_id=evidence_id,
        )

    # Later: here is where we will actually call the MCP API
    # (lab_platform.mcp_layer.mcp_api) and propagate evidence_id downstream.

    return McpDecisionResponse(
        allowed=True,
        reasons=reasons,
        evidence_record_id=evidence_id,
    )
