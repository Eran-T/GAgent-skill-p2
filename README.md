# 🌐 GAgent-Skill-p2: Dynamic Agent Mesh & Agent Registry Discovery Demo

Welcome to the **GAgent-Skill-p2** package! This repository represents **Part 2** of our Agentic Mesh architecture. It implements an automated, registry-driven **Agentic Discovery** system on Google Cloud. 

This package showcases how local coding assistants (such as the IDE, Claude Code, or Antigravity) can dynamically scan a central Google Cloud Agent Registry, parse registration card metadata, discover remote skill configurations, download custom skill markdown instructions directly from Google Cloud Storage (GCS), and dynamically compose authentication and protocol standards to dispatch secure Agent-to-Agent (A2A) queries.

---

## 🎯 The Main Use Case: Dynamic Capability Sync & Remote Consumption

In complex enterprise environments, hardcoding client connections to remote backend agents is brittle and difficult to maintain. **Part 2** resolves this by introducing **Dynamic Agentic Discovery**:

1.  **Registry-Based Capability Listing:** Deployed business agents register their configurations (represented as JSON-RPC cards) to a centralized directory. These cards include a special pointer tag: `[SKILL_URI:gs://<BUCKET_NAME>/path/to/SKILL.md]`.
2.  **On-The-Fly Skill Syncing:** When a local coding assistant encounters a user query requiring an unrecognized business capability, it triggers the registry sync script (`sync_agents.py`).
3.  **Dynamic Skill Compilation:** The script retrieves the agent's registration card, pulls its custom skill instructions from GCS, and compiles it locally as a fresh customization skill (`skills/discovered/<agent_name>/SKILL.md`).
4.  **A2A Query Execution:** The local coding tool reads the newly compiled instructions, obtains authorization via `gcp-auth`, packages a structured payload via `a2a-protocol`, and dispatches the query directly to the remote Agent Platform Agent Runtime.

```
                             [ Local IDE Coding Assistant ]
                                           │
             ┌─────────────────────────────┴─────────────────────────────┐
             │ 1. Scan Central Registry                                  │ 3. Query Deployed Agent via A2A
             ▼                                                           ▼
  [ GCP Agent Registry ]                                     [ Agent Platform Agent Runtime ]
             │ (Read Card Metadata)                                      │ (Executing Tools)
             ▼                                                           ▼
  [ Cloud Storage (GCS) ] ──► (Download SKILL.md)            [ Google-Managed Dataplex MCP ]
```

---

## 📂 Package Directory Structure

```
GAgent-skill-p2/
├── backend/                    # 🤖 Deployed Knowledge Catalog ADK Agent & A2A Wrapper
│   ├── app_utils/              # locked backend utilities
│   │   └── .requirements.txt   # Locked python container dependencies
│   └── agent.py                # Main backend agent wrapping standard A2A JSON-RPC interface
├── skills/                     # 🧭 Packaged Local Customization Skills
│   ├── gcp-auth/                 # 🔑 Skill 1: GCP Authentication Skill
│   │   ├── SKILL.md              # Instructions for token generation
│   │   └── references/
│   │       └── gcp-auth-context.md # python helper for ADC credentials
│   ├── a2a-protocol/             # 💬 Skill 2: JSON-RPC 2.0 A2A Protocol Standard
│   │   ├── SKILL.md              # Instructions on structuring parameters and payloads
│   │   └── references/
│   │       └── a2a-payload-context.md # nested JSON structures and client dispatches
│   ├── agent-discovery/          # 🔍 Skill 3: Agent Registry Discovery Skill
│   │   ├── SKILL.md              # Directives specifying when and how to sync capabilities
│   │   └── scripts/
│   │       └── sync_agents.py    # 🐍 Python Discovery and GCS synchronization script
│   └── knowledge-catalog/        # 📖 GCS-Hosted Master Usage Skill (Simulated source)
│       └── SKILL.md              # Remote specifications pulled during sync
├── pyproject.toml              # Local package dependencies (google-adk, google-cloud-storage, httpx)
├── requirements.txt            # Local development dependencies
├── run_demo.py                 # 🚀 Unified Dynamic Agent Mesh Demo Runner
└── README.md                   # This documentation guide
```

---

## 🛠️ Google `agents-cli` Toolchain Context

The **[`agents-cli`](https://google.github.io/agents-cli/)** is the official command-line manager designed to orchestrate the lifecycle of ADK-based agents. It bridges local testing with enterprise GCP cloud runtimes:

*   **`agents-cli install`**: Installs locked dependencies from `pyproject.toml` into a local virtual environment.
*   **`agents-cli playground`**: Launches an interactive developer UI to inspect, test, and debug connected MCP tool servers.
*   **`agents-cli deploy`**: Dynamically packages your agent container and registers it as an active **Agent Platform Agent Runtime** resource in Google Cloud.

---

## ⚡ Step-by-Step Demonstration Walkthrough

### Step 1: Initialize Dependencies
Install all required package libraries using Astral `uv` or pip:
```bash
uv pip install -e .
# OR
pip install -e .
```

### Step 2: Trigger Dynamic Discovery & Skill Pulling
Run the sync script to query the central Google Cloud Agent Registry. If you are running in an offline or unconfigured environment, the script gracefully falls back to **Simulation Mode** (generating local mock capability cards and pulling remote instructions to ensure the demo is completely resilient):
```bash
python3 ./skills/agent-discovery/scripts/sync_agents.py --project YOUR_PROJECT_ID
```
*   **Expected Result:** The GCS-hosted capability skill is pulled and compiled locally at:
    `skills/discovered/knowledge-catalog-agent/SKILL.md`

### Step 3: Run the Unified A2A Query Flow
Using the instructions from the newly downloaded skill, execute our main demo script:
```bash
python3 run_demo.py
```
This script automates the complete multi-turn lifecycle:
1.  **Discovery:** Scans GCS and downloads the capability card.
2.  **Auth:** Invokes `gcp-auth` to retrieve a dynamic Bearer Token.
3.  **Protocol packaging:** Structures an A2A JSON-RPC 2.0 `message/send` payload containing `contextId` (preserving session history) and the auth token inside `DataPart`.
4.  **Execution stream:** Queries the backend Knowledge Catalog Agent, receiving the table schemas and metadata explored via the backend's Dataplex MCP tool, returning live textual chunks.

---

## 🔗 Additional References & Documentation

*   🛠️ **[`agents-cli`](https://google.github.io/agents-cli/)**: Official developer home and reference documentation for the Google Agents Command Line Toolchain.
*   📖 **[`agent-registry/google-managed-mcps`](https://cloud.google.com/blog/products/ai-machine-learning/google-managed-mcp-servers-are-available-for-everyone?e=48754805)**: Official product release announcement detailing connection architectures for Google Cloud's managed Model Context Protocol (MCP) servers (such as Dataplex Knowledge Catalog).
