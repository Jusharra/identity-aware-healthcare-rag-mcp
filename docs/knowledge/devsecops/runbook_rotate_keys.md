---
title: "Runbook: Rotate API Keys for Clinical RAG"
department: "SecurityEngineering"
clearance: "clinical_sensitive"
region: "US-West"
---

Summary of key rotation steps:

1. Create new API key in the secret manager.
2. Update Azure Functions app settings to use the new key.
3. Redeploy infrastructure via CI/CD.
4. Validate health checks and connectivity.
5. Revoke the old API key and confirm logs show no failures.
