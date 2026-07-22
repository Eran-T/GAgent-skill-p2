#!/usr/bin/env python3
import os
import re
import sys
import json
import subprocess
import httpx
import google.auth
import google.auth.transport.requests

# ==============================================================================
# 🚀 Unified Dynamic Agent Mesh Demo Runner
# This script runs the entire sequence: Discovery -> Auth -> A2A query.
# The endpoint is NOT hardcoded — it is resolved at runtime from the discovered
# agent card (via sync_agents.py), exactly as a real client mesh would.
# Requires only standard python libraries (httpx, google-auth).
# ==============================================================================

GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
NC = "\033[0m"

DISCOVERED_SKILL_PATH = "./skills/discovered/knowledge-catalog-agent/SKILL.md"


def resolve_endpoint(discovered_skill_path: str) -> str:
    """
    Reads the reachable agent endpoint that discovery stamped into the discovered
    skill's `discovery.agent_endpoint` frontmatter field. This is the whole point
    of Part 2: the client learns where to send the query at runtime instead of
    carrying a hand-wired URN.
    """
    try:
        with open(discovered_skill_path) as fh:
            content = fh.read()
        m = re.search(r"agent_endpoint:\s*(\S+)", content)
        if m and m.group(1) not in ("", "UNRESOLVED"):
            return m.group(1)
    except FileNotFoundError:
        pass
    return ""


def run_command(cmd, desc):
    print(f"\n{BLUE}⏳ {desc}...{NC}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"{GREEN}✓ Succeeded!{NC}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"{RED}✗ Failed! Stderr:{NC}\n{e.stderr}")
        raise e


def get_gcp_token():
    print(f"\n{BLUE}🔑 Generating Google Cloud Access Token...{NC}")
    try:
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        print(f"{GREEN}✓ Token acquired programmatically via ADC.{NC}")
        return credentials.token
    except Exception:
        print(f"{YELLOW}⚠️  ADC failed. Falling back to gcloud auth...{NC}")
        token = run_command("gcloud auth print-access-token", "Running gcloud auth print-access-token")
        return token


def main():
    print(f"{BLUE}================================================================{NC}")
    print(f"{BLUE}🌐 STARTING DYNAMIC AGENT MESH DEMO RUNNER{NC}")
    print(f"{BLUE}================================================================{NC}")

    # --- PHASE 1: DYNAMIC AGENT DISCOVERY ---
    run_command(
        "python3 ./skills/agent-discovery/scripts/sync_agents.py",
        "Phase 1: Running Agentic Discovery (syncing GCS skill cards)"
    )

    # Confirm discovered skill file exists
    if os.path.exists(DISCOVERED_SKILL_PATH):
        print(f"{GREEN}✓ Remote capability skill discovered and written to: {DISCOVERED_SKILL_PATH}{NC}")
    else:
        print(f"{RED}✗ Discovered skill file not found!{NC}")
        sys.exit(1)

    # --- PHASE 2: RESOLVE ENDPOINT FROM DISCOVERY (no hardcoded URN) ---
    endpoint = resolve_endpoint(DISCOVERED_SKILL_PATH)
    if not endpoint:
        print(f"{RED}✗ No reachable endpoint advertised in the discovered card. "
              f"Deploy the backend (agents-cli deploy) so deployment_metadata.json "
              f"is populated, then re-run discovery.{NC}")
        sys.exit(1)
    print(f"{GREEN}✓ Resolved agent endpoint dynamically from discovery: {endpoint}{NC}")

    # --- PHASE 3: AUTHENTICATION ---
    token = get_gcp_token()
    user_email = "admin@example.com"

    # --- PHASE 4: DISPATCH A2A message/send QUERY ---
    print(f"\n{BLUE}💬 Phase 4: Dispatching A2A JSON-RPC payload to the deployed agent...{NC}")

    prompt = "Please query the Dataplex catalog to find campaign schemas and tables."

    # A2A JSON-RPC 2.0 message/send, per the a2a-protocol skill: text prompt +
    # a DataPart carrying the delegated caller token so the backend runs Dataplex
    # tools on our behalf. Token is ALSO in the Authorization header for transport.
    a2a_request = {
        "jsonrpc": "2.0",
        "id": "demo-req-001",
        "method": "message/send",
        "params": {
            "contextId": "demo-session-001",
            "message": {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": prompt},
                    {"kind": "data", "data": {
                        "user_id": user_email,
                        "user_access_token": token,
                    }},
                ],
            },
        },
    }

    # The Agent Runtime `:query` hook dispatches `input` to handle_a2a_request().
    payload = {"class_method": "query", "input": a2a_request}

    print(f"{BLUE}🚀 Sending A2A query payload...{NC}")
    print(f"Endpoint: {endpoint}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"\n{GREEN}================================================================{NC}")
        print(f"{GREEN}📊 AGENT EXECUTION RESPONSE:{NC}")
        print(f"{GREEN}================================================================{NC}")

        r = httpx.post(endpoint, json=payload, headers=headers, timeout=60.0)
        if r.status_code != 200:
            print(f"{RED}✗ Request failed with status {r.status_code}:{NC}\n{r.text}")
            sys.exit(1)

        data = r.json()

        # A2A JSON-RPC error object
        if "error" in data:
            print(f"{RED}✗ Agent returned JSON-RPC error: {data['error']}{NC}")
            sys.exit(1)

        # Extract text from result/message/parts per the a2a-protocol response schema
        result = data.get("result", {})
        parts = result.get("message", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                print(part["text"], end="", flush=True)

        artifacts = result.get("artifacts", [])
        if artifacts:
            print(f"\n\n{YELLOW}📎 Artifacts returned:{NC}")
            for art in artifacts:
                print(f"  - {art}")

        print(f"\n{GREEN}================================================================{NC}")
        print(f"{GREEN}🎉 Demo completed successfully!{NC}\n")

    except Exception as e:
        print(f"{RED}✗ HTTP dispatch failed: {str(e)}{NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
