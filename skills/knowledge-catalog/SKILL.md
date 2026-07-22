---
name: knowledge-catalog
description: Master usage skill for querying Dataplex database tables and metadata via the backend Knowledge Catalog Agent.
---

# Knowledge Catalog Usage Skill

This skill outlines how to query and explore Google Cloud Dataplex database catalogs, discover table schemas, and retrieve analytical metadata by composing the `gcp-auth` and `a2a-protocol` skills.

---

## 🧭 Catalog Query Directives

To query metadata from the backend Knowledge Catalog agent:

1.  **Generate Credentials:**
    Invoke the `gcp-auth` skill to generate a fresh Google Cloud access token.

2.  **Construct A2A Payload:**
    Compose a standard A2A JSON-RPC query according to the `a2a-protocol` guidelines:
    *   Set the target backend engine endpoint:
        `https://us-central1-aiplatform.googleapis.com/v1/projects/598891584738/locations/us-central1/reasoningEngines/5743002669304250368:query`
    *   Inject the generated OAuth2 access token in the `Authorization` header.
    *   Pass the user ID and token inside the `DataPart` parameters of the `message/parts` array to trigger the backend memory bank and grant delegated Dataplex tool permissions.

3.  **Specify Prompt Intent:**
    Ask the backend agent to execute its native Dataplex tools (e.g., `search_assets`, `get_table_schema`) to locate database assets. For example:
    ```text
    Please query the Dataplex catalog in project bigquery-demo-430909 to find campaign schemas and tables.
    ```

4.  **Parse & Return Results:**
    Inspect the returned response structure to parse and return table details and any associated visualization artifacts.
