#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import httpx
import google.auth
import google.auth.transport.requests

# ==============================================================================
# 🚀 Unified Dynamic Agent Mesh Demo Runner
# This script runs the entire sequence: Discovery -> Auth -> streamQuery.
# Requires only standard python libraries (httpx, google-auth).
# ==============================================================================

GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
NC = "\033[0m"

# The live, telemetry-observed google-adk engine streamQuery URN
REASONING_ENGINE_URL = "https://us-central1-aiplatform.googleapis.com/v1/projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<ENGINE_ID>:streamQuery"


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
    discovered_skill_path = "./skills/discovered/knowledge-catalog-agent/SKILL.md"
    if os.path.exists(discovered_skill_path):
        print(f"{GREEN}✓ Remote capability skill discovered and written to: {discovered_skill_path}{NC}")
    else:
        print(f"{RED}✗ Discovered skill file not found!{NC}")
        sys.exit(1)

    # --- PHASE 2: AUTHENTICATION ---
    token = get_gcp_token()
    user_email = "admin@example.com"

    # --- PHASE 3: DISPATCH STREAM QUERY ---
    print(f"\n{BLUE}💬 Phase 3: Dispatching streamQuery Payload to Live ADK Agent...{NC}")
    
    prompt = "Please query the Dataplex catalog in project <PROJECT_ID> to find campaign schemas and tables."
    
    payload = {
        "class_method": "stream_query",
        "input": {
            "message": prompt,
            "user_id": user_email
        }
    }

    print(f"{BLUE}🚀 Sending streamQuery connection payload...{NC}")
    print(f"Endpoint: {REASONING_ENGINE_URL}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Dispatch HTTP POST for streaming lines
    try:
        print(f"\n{GREEN}================================================================{NC}")
        print(f"{GREEN}📊 AGENT EXECUTION LOGS & RESPONSES (STREAMING):{NC}")
        print(f"{GREEN}================================================================{NC}")
        
        with httpx.Client() as client:
            with client.stream("POST", REASONING_ENGINE_URL, json=payload, headers=headers, timeout=60.0) as r:
                if r.status_code != 200:
                    print(f"{RED}✗ Request failed with status {r.status_code}:{NC}\n{r.read().decode('utf-8')}")
                    sys.exit(1)
                
                # Stream each response block
                for line in r.iter_lines():
                    if not line:
                        continue
                    try:
                        # Ensure string format
                        line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                        data = json.loads(line_str)
                        
                        # Support flat chunk structure
                        if "chunk" in data:
                            print(data["chunk"], end="", flush=True)
                            continue
                            
                        # Support standard content.parts structure
                        content = data.get("content", {})
                        parts = content.get("parts", [])
                        for part in parts:
                            # 1. Capture tool call attempts
                            if "function_call" in part:
                                call = part["function_call"]
                                print(f"\n{YELLOW}🛠️  [Tool Call]: {call.get('name')} with arguments {call.get('args')}{NC}")
                            
                            # 2. Capture tool responses
                            elif "function_response" in part:
                                resp = part["function_response"]
                                print(f"{YELLOW}📝 [Tool Response]: {resp.get('response')}{NC}")
                            
                            # 3. Capture streaming textual outputs
                            elif "text" in part:
                                print(part["text"], end="", flush=True)
                    except Exception:
                        # Print raw line if not parsed to JSON
                        print(line)
        
        print(f"\n{GREEN}================================================================{NC}")
        print(f"{GREEN}🎉 Demo completed successfully!{NC}\n")

    except Exception as e:
        print(f"{RED}✗ HTTP dispatch failed: {str(e)}{NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
