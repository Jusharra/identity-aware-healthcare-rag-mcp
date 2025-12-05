import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml
from .local_knowledge import search_local_docs
from lab_platform.rag_layer import local_knowledge


try:
    import pinecone
except Exception:
    pinecone = None   # allows config + namespace tests without live Pinecone


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "config",
    "rag_config.yaml",
)


@dataclass
class RAGConfig:
    index_name: str
    environment: str
    namespaces: Dict[str, Dict[str, Any]]
    defaults: Dict[str, Any]


class RAGOrchestrator:
    """
    Identity-aware RAG orchestrator.

    - Maps roles/scopes -> Pinecone namespaces
    - Builds metadata filters from claims
    - (Later) calls Azure OpenAI / OpenAI for final answer
    """

    def __init__(self, config_path: str = CONFIG_PATH) -> None:
        self.config = self._load_config(config_path)
        self._pinecone_index = None

    def _load_config(self, path: str) -> RAGConfig:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        pinecone_cfg = raw.get("pinecone", {})
        namespaces = raw.get("namespaces", {})
        defaults = raw.get("defaults", {})

        return RAGConfig(
            index_name=pinecone_cfg.get("index_name", "healthcare-rag"),
            environment=pinecone_cfg.get("environment", "us-west1-gcp"),
            namespaces=namespaces,
            defaults=defaults,
        )

    # ---------- Namespace selection ----------

    def select_namespace(
        self,
        role: str,
        requested_scope: str,
    ) -> Optional[str]:
        """
        Pick a namespace based on role + rag_scope.

        Returns namespace name or None if no suitable namespace exists.
        """
        for ns_name, ns_cfg in self.config.namespaces.items():
            allowed_roles = ns_cfg.get("allowed_roles", [])
            rag_scopes = ns_cfg.get("rag_scopes", [])
            if role in allowed_roles and requested_scope in rag_scopes:
                return ns_name
        return None

    # ---------- Pinecone index helper ----------

    def _get_index(self):
        """
        Lazy-init Pinecone index. For now we only need it for demos.
        Will no-op if pinecone lib isn't installed or API key missing.
        """
        global pinecone  # noqa: PLW0603
        if pinecone is None:
            raise RuntimeError("pinecone package is not installed")

        if self._pinecone_index is None:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                raise RuntimeError("PINECONE_API_KEY env var not set")

            # Wrap the new Pinecone behavior so failures become RuntimeError
            try:
                # This will blow up on new pinecone package with "init is no longer..."
                pinecone.init(api_key=api_key, environment=self.config.environment)
                self._pinecone_index = pinecone.Index(self.config.index_name)
            except Exception as exc:
                # Normalize all Pinecone init issues into RuntimeError so query()
                # can treat this as "dry-run" mode for the lab.
                raise RuntimeError(f"Pinecone init failed: {exc}") from exc

        return self._pinecone_index


    # ---------- Metadata filter builder ----------

    def build_metadata_filter(
        self,
        claims: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a Pinecone filter object from identity claims.
        You can expand this as needed.
        """
        filt: Dict[str, Any] = {}

        if dept := claims.get("department"):
            filt["department"] = dept

        if clinic_id := claims.get("clinic_id"):
            filt["clinic_id"] = clinic_id

        if clearance := claims.get("clearance"):
            # You might tag docs with "clearance_level"
            filt["clearance_level"] = clearance

        if region := claims.get("region"):
            filt["region"] = region

        return filt

    # ---------- Main RAG entrypoint ----------

    def query(
        self,
        query_text: str,
        claims: Dict[str, Any],
        requested_scope: str,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Identity-aware RAG query.

        Returns a structured payload that your API layer can
        enrich with LLM calls and evidence logging.
        """
        role = claims.get("role")
        if not role:
            return {
                "allowed": False,
                "namespace": None,
                "matches": [],
                "reason": "Missing role in claims (claims.role is required)",
            }


        namespace = self.select_namespace(role, requested_scope)
        if namespace is None:
            return {
                "allowed": False,
                "namespace": None,
                "matches": [],
                "reason": f"No namespace configured for role={role}, scope={requested_scope}",
            }

        # Build metadata filter
        metadata_filter = self.build_metadata_filter(claims)
        top_k = top_k or self.config.defaults.get("top_k", 5)

        # For now, we allow you to run this without a live Pinecone index.
        index = None
        matches: List[Dict[str, Any]] = []

        try:
            index = self._get_index()
        except RuntimeError as exc:
            # Offline / lab mode: use local markdown knowledge instead of Pinecone
            local = local_knowledge.search_local_docs(
                namespace=namespace,
                query_text=query_text,
                claims=claims,
                max_docs=top_k,
            )

            return {
                "allowed": True,
                "namespace": namespace,
                "matches": local.get("docs", []),
                "reason": f"RAG using local knowledge instead of Pinecone: {exc}",
                "query_text": query_text,
                "metadata_filter": metadata_filter,
                "local_answer": local.get("answer"),
            }



        # If Pinecone is available, actually query
        res = index.query(
            namespace=namespace,
            top_k=top_k,
            include_metadata=True,
            vector=[],  # we'll switch to embedding-based later
            filter=metadata_filter or None,
        )

        for match in res.get("matches", []):
            matches.append(
                {
                    "id": match.get("id"),
                    "score": match.get("score"),
                    "metadata": match.get("metadata", {}),
                }
            )

        return {
            "allowed": True,
            "namespace": namespace,
            "matches": matches,
            "query_text": query_text,
            "metadata_filter": metadata_filter,
        }
    # ---- STUBBED ANSWER (no Pinecone/OpenAI yet) ----
        demo_answer = (
            f"[DEMO ANSWER] RAG would query namespace '{namespace}' "
            f"for scope '{requested_scope}' with user role '{role}'. "
            f"Query: {query_text}"
        )

        return {
            "allowed": True,
            "namespace": namespace,
            "answer": demo_answer,
            "claims_snapshot": {
                "sub": claims.get("sub"),
                "role": role,
                "department": claims.get("department"),
                "clinic_id": claims.get("clinic_id"),
                "clearance": claims.get("clearance"),
                "region": claims.get("region"),
            },
        }    