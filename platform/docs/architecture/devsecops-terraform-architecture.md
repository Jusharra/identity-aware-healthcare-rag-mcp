# DevSecOps & Terraform Architecture – Identity-Aware Healthcare RAG + MCP on Azure

This section documents the **DevSecOps and Terraform architecture** that supports the Identity-Aware Healthcare RAG + Identity Governance MCP platform.

The goal is to show how we:

- Provision cloud resources safely with **Terraform**
- Build, scan, and deploy our **MCP + RAG services** with **Azure DevOps**
- Store all images in a hardened **Azure Container Registry**
- Use **federated identities** instead of static secrets
- Centralize **logs and evidence** for GRC and audit


## 1. Core Azure Services (High-Level)

At a very high level, the DevSecOps pipeline leverages the following Azure services:

### Azure DevOps

- Provides end-to-end **CI/CD pipelines** and project management.
- Automates:
  - Builds
  - Tests
  - Security scans
  - Deployments (Terraform + app)
- Pipelines are defined as YAML in GitHub, keeping everything version-controlled.

### Azure Container Registry (ACR)

- Secure, private registry for storing **Docker images**.
- Holds:
  - MCP API container image
  - (Later) RAG orchestration workers or other microservices
- Only workloads authenticated via **managed/federated identity** can pull/push.

### Federated / User-Assigned Identity

- Used by Azure DevOps and runtime workloads to access Azure resources **without secrets**.
- Replaces:
  - Service principal passwords
  - Access keys injected as plain-text
- Aligns with:
  - Zero trust
  - “No long-lived secrets in CI/CD” practices

### Resource Group

- Logical container for everything in this lab:
  - Storage account for evidence
  - (Later) Functions, Container Apps, APIM, etc.
- Makes governance, lifecycle management, and teardown easier.

### Azure Resource Manager Service Connection (AzureRM)

- Connects **Azure DevOps** pipelines to your Azure subscription.
- Uses **federated authentication** (OIDC) instead of static secrets.
- Enables:
  - Terraform `plan` / `apply`
  - Resource deployments
  - Role assignments tied to least privilege


## 2. DevSecOps Pipeline Flow (High-Level)

End-to-end flow for this lab:

1. **Developer commits code** to GitHub  
   - Changes may include:
     - MCP tools / MCP API
     - Azure Functions (identity gateway, MCP router, RAG orchestrator)
     - Terraform modules (evidence storage, infra)
     - Policy-as-Code (OPA/Rego)

2. **Azure DevOps pipeline is triggered**  
   - YAML pipeline definition lives in the repo.
   - The pipeline orchestrates:
     - Build
     - Test
     - Scan
     - Deploy

3. **Build stage (Python + container image)**  
   - Python dependencies are installed.
   - Linting and formatting checks run (e.g., `flake8`, `black`).
   - MCP API and/or Function app is packaged as a **container image**.

4. **Security scanning stage**

   - Python source and dependencies are scanned for vulnerabilities.
   - The containerized application image is scanned with tools such as:
     - **ZAP by Checkmarx** (dynamic / web security tests)
     - **Trivy** (image and dependency scanning)
   - This enforces DevSecOps practices **before** anything reaches production.

5. **Terraform validation & apply**

   - Terraform validates the configuration for:
     - Evidence storage (storage account + containers)
     - (Later) Functions, Container Apps, networking
   - On approval, Terraform `apply` provisions or updates resources:
     - Resource group
     - Storage account
     - `docs-raw`, `logs`, `evidence` containers (all private)

6. **Publish to Azure Container Registry**

   - If all tests and scans pass:
     - The containerized application image is pushed to **Azure Container Registry**.
   - Tags include:
     - Git commit SHA
     - Environment (`dev`, `stage`, etc.)

7. **Deploy from ACR to runtime**

   - Downstream stages (later in the lab) will:
     - Pull the image from ACR
     - Deploy to Azure Container Apps or Functions with custom handlers
   - All runtime identities use **managed/federated identity** to:
     - Read from ACR
     - Write to Storage Account (logs/evidence)
     - Call other Azure services


## 3. Terraform Evidence Storage Module (This Lab)

The first Terraform module in this project provisioned:

- A **resource group**
- An **Azure Storage Account**
- Three **private containers**:
  - `docs-raw` – healthcare policies, guidelines, and clinical documents for ingestion
  - `logs` – application logs and synchronized MCP logs
  - `evidence` – weekly governance & evidence bundles (CSV/JSON/txt)

This module:

- Disables **public blob access** for security.
- Enables **delete retention** for 30 days to prevent accidental data loss.
- Attaches **system-assigned identity** to the storage account.
- Applies **standard tags** such as:
  - `environment = dev`
  - `owner = grc-platform`


## 4. Why This Matters for GRC & AI Governance

From a CISO / auditor perspective, this architecture shows:

- **No “snowflake” infrastructure** – everything is Terraform + YAML pipelines.
- **No long-lived secrets** in pipelines – access via federated/managed identity.
- **Security built into the pipeline**:
  - Formatting + linting
  - Image + dependency scans
  - Terraform validation
- **Centralized, private evidence store** for:
  - MCP tool usage
  - RAG access patterns
  - Weekly compliance summaries

This DevSecOps + Terraform layer is the backbone that makes the
Identity-Aware Healthcare RAG + MCP platform **auditable, reproducible, and secure**.
