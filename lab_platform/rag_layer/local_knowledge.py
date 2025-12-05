# lab_platform/rag_layer/local_knowledge.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List


# repo_root / docs / knowledge / <namespace>
BASE_DIR = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = BASE_DIR / "docs" / "knowledge"

# Map RAG namespace -> folder name under docs/knowledge
NAMESPACE_DIR_MAP = {
    "clinical": "clinical",
    "company": "company",
    "grc": "grc",
    "devsecops": "devsecops",
}


def _load_docs_for_namespace(namespace: str) -> List[Dict[str, Any]]:
    """
    Load simple markdown docs for the given namespace.

    Each doc is returned as:
    {
      "path": "...",
      "title": "...",
      "preview": "first few lines..."
    }
    """
    folder_name = NAMESPACE_DIR_MAP.get(namespace)
    if not folder_name:
        return []

    folder = KNOWLEDGE_ROOT / folder_name
    if not folder.exists():
        return []

    docs: List[Dict[str, Any]] = []

    for path in sorted(folder.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        title = lines[0] if lines else path.stem
        preview = "\n".join(lines[:5])  # first few lines as preview

        docs.append(
            {
                "path": str(path),
                "title": title,
                "preview": preview,
            }
        )

    return docs


def search_local_docs(
    namespace: str,
    query_text: str,
    claims: Dict[str, Any],
    max_docs: int = 5,
) -> Dict[str, Any]:
    """
    Very small "fake RAG" that:
    - loads namespace docs
    - returns up to max_docs
    - builds a demo answer string using role/department
    """
    docs = _load_docs_for_namespace(namespace)
    docs = docs[:max_docs]

    role = claims.get("role", "Unknown")
    dept = claims.get("department", "Unknown")

    if not docs:
        answer = (
            f"[LOCAL DEMO] No local docs found for namespace '{namespace}'. "
            f"User role='{role}', department='{dept}'. "
            f"Query: {query_text}"
        )
    else:
        titles = ", ".join(d["title"] for d in docs)
        answer = (
            f"[LOCAL DEMO] Answer for role='{role}', dept='{dept}', "
            f"namespace='{namespace}'.\n"
            f"Query: {query_text}\n"
            f"Relevant local docs: {titles}"
        )

    return {
        "docs": docs,
        "answer": answer,
    }
