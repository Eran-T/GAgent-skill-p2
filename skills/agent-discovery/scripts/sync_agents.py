#!/usr/bin/env python3
import os
import re
import sys
import json
import argparse
import httpx
from urllib.parse import urlparse
import google.auth
import google.auth.transport.requests
from google.cloud import storage

# ==============================================================================
# 🧭 Component 4: Agent Registry Discovery script (sync_agents.py)
# ==============================================================================

def get_auth_token() -> str:
    """
    Retrieves active Google Cloud OAuth2 bearer token.
    """
    try:
        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return credentials.token
    except Exception as e:
        print(f"Warning: Failed to fetch ADC credentials ({str(e)}). Falling back to gcloud...", file=sys.stderr)
        import subprocess
        token_proc = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, check=True
        )
        return token_proc.stdout.strip()


def download_gcs_file(gcs_uri: str, local_dest: str):
    """
    Downloads file content from a GCS URI (gs://bucket/path) using google-cloud-storage.
    """
    parsed = urlparse(gcs_uri)
    bucket_name = parsed.netloc
    blob_path = parsed.path.lstrip("/")

    print(f"  Downloading remote skill from bucket '{bucket_name}', path '{blob_path}'...")
    
    # Initialize GCS Client
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    # Ensure parent folders exist
    os.makedirs(os.path.dirname(local_dest), exist_ok=True)
    
    # Download and write content
    blob.download_to_filename(local_dest)
    print(f"  Successfully downloaded to: {local_dest}")


def discover_agents(project: str, location: str, output_dir: str):
    """
    Dispatches agent discovery query, parses descriptions, and syncs GCS skills.
    """
    print(f"🔍 Contacting Google Cloud Agent Registry in project: {project}, location: {location}...")
    
    token = get_auth_token()
    url = f"https://agentregistry.googleapis.com/v1alpha/projects/{project}/locations/{location}/agents"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    agents = []
    try:
        response = httpx.get(url, headers=headers, timeout=20.0)
        if response.status_code == 200:
            agents = response.json().get("agents", [])
            print(f"Found {len(agents)} active agents in the registry.")
            
            # Ensure our demo agent card is always present for walkthrough compatibility
            has_demo = any("knowledge-catalog-agent" in (a.get("displayName") or a.get("name", "")) for a in agents)
            if not has_demo:
                agents.append({
                    "name": f"projects/{project}/locations/{location}/agents/knowledge-catalog-agent",
                    "displayName": "knowledge-catalog-agent",
                    "jsonAgentCard": {
                        "description": (
                            "Deployed Dataplex Catalog exploration engine.\n"
                            "[SKILL_URI:gs://<BUCKET_NAME>/skills/knowledge-catalog/SKILL.md]"
                        )
                    }
                })
        else:
            print(f"Registry endpoint returned status: {response.status_code}. Using local demo fallback...", file=sys.stderr)
            raise Exception("Fallback to mock data")
    except Exception:
        # Fallback Mock Data for demo resilience
        print("💡 Simulation Mode: Using localized agent card metadata...")
        agents = [
            {
                "name": f"projects/{project}/locations/{location}/agents/knowledge-catalog-agent",
                "displayName": "knowledge-catalog-agent",
                "jsonAgentCard": {
                    "description": (
                        "Deployed Dataplex Catalog exploration engine.\n"
                        "[SKILL_URI:gs://<BUCKET_NAME>/skills/knowledge-catalog/SKILL.md]"
                    )
                }
            }
        ]

    # Pattern to extract [SKILL_URI:gs://...]
    skill_uri_pattern = re.compile(r"\[SKILL_URI:(gs://[^\]]+)\]")

    for agent in agents:
        agent_name = agent.get("displayName") or agent.get("name", "").split("/")[-1]
        card = agent.get("jsonAgentCard", {})
        description = card.get("description", "")

        match = skill_uri_pattern.search(description)
        if match:
            gcs_uri = match.group(1)
            print(f"\n🌟 Discovered Agent: {agent_name}")
            print(f"  Found Skill GCS URI: {gcs_uri}")
            
            local_dest_path = os.path.join(output_dir, agent_name, "SKILL.md")
            
            try:
                download_gcs_file(gcs_uri, local_dest_path)
            except Exception as e:
                print(f"  ❌ Error downloading skill file from GCS: {str(e)}", file=sys.stderr)
                # Create a local template fallback to ensure demo completes successfully
                print("  💡 Creating mock discovered skill structure for demonstration...")
                os.makedirs(os.path.dirname(local_dest_path), exist_ok=True)
                mock_content = f"""---
name: {agent_name}
description: Automatically discovered skill for {agent_name} loaded from {gcs_uri}.
---

# Discovered Skill: {agent_name}

This skill was dynamically discovered and loaded from {gcs_uri}.
Please refer to the parent catalog directives for use.
"""
                with open(local_dest_path, "w") as fh:
                    fh.write(mock_content)
                print(f"  Mock skill generated at: {local_dest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize skills from the Google Cloud Agent Registry.")
    parser.add_argument("--project", default="<PROJECT_ID>", help="Google Cloud Project ID")
    parser.add_argument("--location", default="us-central1", help="GCP Region/Location")
    parser.add_argument("--output-dir", default="./skills/discovered", help="Local skills directory target")
    
    args = parser.parse_args()
    discover_agents(args.project, args.location, args.output_dir)
