---
name: agent-discovery
description: Scans the organization's central Google Cloud Agent Registry to dynamically discover and download remote skills from GCS.
---

# Agent Registry Discovery Skill

This skill provides a dynamic discovery mechanism to scan the central Google Cloud Agent Registry, locate registered agent cards, extract their remote skill locations, and install them on the fly.

---

## 🧭 Discovery Directives

1.  **When to Trigger Discovery:**
    Whenever the user requests an analytical capability, data querying service, or chart representation pattern that is **NOT** currently documented or supported in the local `skills/` folder, the agent **MUST** invoke the dynamic discovery sync process.

2.  **How to Execute Discovery:**
    Run the unified sync script in the workspace using the local Python interpreter:
    ```bash
    python3 ./skills/agent-discovery/scripts/sync_agents.py --project bigquery-demo-430909 --location us-central1
    ```

3.  **Post-Discovery Compilation:**
    *   Once the script finishes execution, the remote skill description file will be written to:
        `skills/discovered/{agent_name}/SKILL.md`
    *   The agent must instantly read and parse the newly discovered `SKILL.md` to acquire the required instructions and execute the user's prompt.
