# platform/mcp_layer/mcp_api/app.py

from __future__ import annotations

import os
import secrets
from typing import Optional, Any, Dict

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dotenv import load_dotenv  # <- must be here

from lab_platform.mcp_layer.mcp_server import MCPServer
from lab_platform.rag_layer.orchestrator import RAGOrchestrator

load_dotenv(override=True)     # <- must be called before we read envs # Loads .env into environment variables


API_KEY_ENV = "MCP_API_KEY"
API_KEY_HEADER_NAME = "X-API-Key"

app = FastAPI(title="Identity Governance MCP + RAG API", version="0.1.0")

# MCP runtime
mcp_server = MCPServer()

# RAG orchestrator (your existing class, untouched)
rag_orchestrator = RAGOrchestrator()


def get_expected_api_key() -> str:
    key = os.getenv(API_KEY_ENV)
    if not key:
        # Misconfiguration: we fail closed
        raise RuntimeError(f"{API_KEY_ENV} environment variable not set")
    return key


async def verify_api_key(x_api_key: str | None) -> None:
    expected = get_expected_api_key()
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        # Default-deny posture: don't reveal details
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------
# RAG request model + claims
# ---------------------------

class RAGQuery(BaseModel):
    query: str
    scope: str


def build_debug_claims(request: Request) -> Dict[str, Any]:
    """
    Temporary helper so you can test RBAC/ABAC without Entra ID yet.

    Later this will be replaced with real JWT validation.
    """
    role = request.headers.get("X-Debug-Role", "Physician")

    return {
        "sub": f"debug-{role.lower()}",
        "role": role,
        "department": request.headers.get("X-Debug-Department", "Cardiology"),
        "clinic_id": request.headers.get("X-Debug-Clinic-Id", "clinic_01"),
        "clearance": request.headers.get("X-Debug-Clearance", "clinical_sensitive"),
        "region": request.headers.get("X-Debug-Region", "US-West"),
    }


# ---------------------------
# MCP TOOL ENDPOINT (existing)
# ---------------------------

@app.post("/mcp/run")
async def run_tool(
    request: Request,
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER_NAME),
) -> JSONResponse:
    # 1) API key gate
    await verify_api_key(x_api_key)

    # 2) Parse body
    body: Dict[str, Any] = await request.json()
    tool_name = body.get("tool")
    input_data = body.get("input", {}) or {}
    caller_claims = body.get("caller_claims", {}) or {}

    # 3) Delegate to MCP runtime
    result = mcp_server.run_tool(tool_name, input_data, caller_claims)
    status = 200 if result.get("success") else 400

    return JSONResponse(content=result, status_code=status)


# ---------------------------
# RAG ENDPOINT (new)
# ---------------------------

@app.post("/rag/query")
async def identity_aware_rag(
    payload: RAGQuery,
    request: Request,
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER_NAME),
) -> JSONResponse:
    """
    Identity-aware RAG gateway.

    - Uses the same API key protection as MCP.
    - Derives identity claims (for now) from X-Debug-* headers.
    - Delegates all RBAC/ABAC + namespace logic to your RAGOrchestrator.
    """
    # 1) API key gate
    await verify_api_key(x_api_key)

    # 2) Build identity claims (later: real JWT)
    claims = build_debug_claims(request)

    # 3) Call your existing orchestrator
    result = rag_orchestrator.query(
        query_text=payload.query,
        claims=claims,
        requested_scope=payload.scope,
    )

    # 4) Enforce allow/deny at the API boundary
    if not result.get("allowed"):
        # We pass the full result in the error body so auditors can see *why*
        raise HTTPException(status_code=403, detail=result)

    return JSONResponse(content=result, status_code=200)
