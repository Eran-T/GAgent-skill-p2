---
name: gcp-auth
description: Instructions for obtaining Google Cloud authentication tokens for HTTP service access and user delegation.
---

# GCP Authentication Skill

This skill instructs the agent on how to negotiate and generate Google Cloud authorization credentials dynamically for use in A2A headers, data delegation payloads, or local SDK client setups.

---

## 🧭 Authentication Directives

When invoking any external GCP service, reasoning engines, or agent registry APIs:

1.  **Check for Active Credentials:**
    Attempt to fetch an active token. If the process raises authorization or authentication errors, prompt the user or execute:
    ```bash
    gcloud auth application-default login
    ```
2.  **Generate Dynamic OAuth2 Bearer Tokens:**
    Generate a fresh, short-lived Google Cloud Access Token using the gcloud command:
    ```bash
    gcloud auth print-access-token
    ```
3.  **Data Delegation Pattern:**
    When preparing communication payloads for downstream backend agents, inject this access token inside the `parts` block of your JSON-RPC payloads as the user credential (enabling the backend to act on behalf of the caller).

---

## 📖 Context & Commands Syntax Reference

Refer to the complete syntax reference document:
[references/gcp-auth-context.md](./references/gcp-auth-context.md)
