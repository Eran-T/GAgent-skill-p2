---
name: a2a-protocol
description: Comprehensive guide to constructing and parsing JSON-RPC 2.0 payloads for the Agent-to-Agent (A2A) communication standard.
---

# A2A Protocol Skill

This skill defines the technical rules and formats for executing cross-agent calls (A2A) over HTTP REST using the standardized JSON-RPC 2.0 payload format.

---

## 🧭 Protocol Directives

### 1. Header Population
When sending requests to a remote agent endpoint, the client must authenticate using an active Google Cloud credential.
*   **Action:** Call the `gcp-auth` skill to retrieve a fresh OAuth2 token.
*   **Header:** Inject the retrieved token as `Authorization: Bearer <token>`.

### 2. Constructing the JSON-RPC Payload (`message/send`)
The root JSON-RPC request must define `jsonrpc: "2.0"`, an alphanumeric `id`, a target `method: "message/send"`, and nested `params`:

*   **Context/Session Key (`contextId`):** Supply the active thread session identifier to preserve context state across multi-turn queries.
*   **Prompt Parts (`message/parts`):**
    *   **TextPart:** Contains the user query or instruction prompt.
        ```json
        {"kind": "text", "text": "Locate marketing campaign table."}
        ```
    *   **DataPart (Delegation Credentials):** Injects user metadata to authorize downstream tool executions:
        ```json
        {
          "kind": "data",
          "data": {
            "user_id": "user@example.com",
            "user_access_token": "<access_token>"
          }
        }
        ```

### 3. Long-Term Memory Extraction
To trigger memory-bank history recall at the backend reasoning engine, you **MUST** pass the `user_id` inside the `DataPart` payload block. This prompts the Vertex AI Agent Engine to pull the caller's unique memory-bank associations automatically.

### 4. Parsing Responses
*   **Session State:** Inspect the JSON-RPC `result` block to extract the active `contextId`. Persist this key and pass it in subsequent turns to load the exact conversation context.
*   **Artifacts:** Extract any returned analytical data, files, or visualization references from the `result/artifacts` list.

---

## 📖 Complete JSON Payload Specs & Code Blueprints

For complete, copy-pasteable Python implementation codes and nested JSON examples, read:
[references/a2a-payload-context.md](./references/a2a-payload-context.md)
