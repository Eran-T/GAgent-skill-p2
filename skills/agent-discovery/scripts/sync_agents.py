#!/usr/bin/env python3
import os
import re
import sys
import json
import shutil
import argparse
import httpx
from urllib.parse import urlparse
import google.auth
import google.auth.transport.requests
from google.cloud import storage

# ==============================================================================
# 🧭 Component 4: Agent Registry Discovery script (sync_agents.py)
# ==============================================================================

# Repo root (…/GAgent-skill-p2), resolved relative to this script's location so
# the discovery works regardless of the current working directory.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Local "GCS-hosted master" skill used as the simulation-mode source. In a real
# deployment this same file is what lives at the card's gs:// SKILL_URI.
LOCAL_MASTER_SKILL = os.path.join(REPO_ROOT, "skills", "knowledge-catalog", "SKILL.md")

# Deployment metadata written by `agents-cli deploy`; the single source of truth
# for the live runtime endpoint used in simulation mode.
DEPLOYMENT_METADATA = os.path.join(REPO_ROOT, "deployment_metadata.json")


def load_deployed_endpoint() -> str:
    """
    Reads the deployed Agent Runtime resource ID from deployment_metadata.json
    and derives the aiplatform :query endpoint. Returns "" if unavailable.
    """
    try:
        with open(DEPLOYMENT_METADATA) as fh:
            meta = json.load(fh)
        runtime_id = meta.get("remote_agent_runtime_id", "")
        # runtime_id: projects/<num>/locations/<loc>/reasoningEngines/<id>
        m = re.search(r"locations/([^/]+)/", runtime_id)
        location = m.group(1) if m else "us-central1"
        if runtime_id:
            return (
                f"https://{location}-aiplatform.googleapis.com/v1/"
                f"{runtime_id}:query"
            )
    except Exception:
        pass
    return ""

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


def _demo_card(project: str, location: str) -> dict:
    """
    Builds the demo agent registration card. The card advertises BOTH pointers a
    client needs for fully dynamic consumption: the remote skill location
    (SKILL_URI) and the reachable query endpoint (AGENT_URI). The endpoint is
    sourced from deployment_metadata.json so nothing is hand-wired.
    """
    endpoint = load_deployed_endpoint()
    endpoint_tag = f"\n[AGENT_URI:{endpoint}]" if endpoint else ""
    return {
        "name": f"projects/{project}/locations/{location}/agents/knowledge-catalog-agent",
        "displayName": "knowledge-catalog-agent",
        "jsonAgentCard": {
            "description": (
                "Deployed Dataplex Catalog exploration engine.\n"
                "[SKILL_URI:gs://<BUCKET_NAME>/skills/knowledge-catalog/SKILL.md]"
                f"{endpoint_tag}"
            )
        },
    }


def _inject_discovery_metadata(skill_path: str, agent_name: str, gcs_uri: str, endpoint: str):
    """
    Stamps the freshly discovered SKILL.md with a `discovery` frontmatter block so
    the client agent can read the resolved endpoint directly from the skill —
    removing any need for a hardcoded URN.
    """
    with open(skill_path) as fh:
        content = fh.read()

    discovery_block = (
        "discovery:\n"
        f"  source_uri: {gcs_uri}\n"
        f"  agent_endpoint: {endpoint or 'UNRESOLVED'}\n"
    )

    if content.startswith("---"):
        # Insert the discovery block just before the closing frontmatter fence.
        parts = content.split("---", 2)
        # parts[1] is the existing frontmatter body.
        new_frontmatter = parts[1].rstrip("\n") + "\n" + discovery_block
        content = "---" + new_frontmatter + "---" + parts[2]
    else:
        content = f"---\nname: {agent_name}\n{discovery_block}---\n\n" + content

    with open(skill_path, "w") as fh:
        fh.write(content)


def _compile_from_local_master(local_dest_path: str, agent_name: str, gcs_uri: str, endpoint: str) -> bool:
    """
    Simulation compiler: the local master skill IS the file that would live at
    gcs_uri, so copy it to produce a *usable* discovered skill. Returns True on
    success.
    """
    if not os.path.exists(LOCAL_MASTER_SKILL):
        print(f"  ❌ Local master skill not found at {LOCAL_MASTER_SKILL}; cannot compile discovered skill.", file=sys.stderr)
        return False
    print("  💡 Simulation Mode: compiling discovered skill from local master source...")
    os.makedirs(os.path.dirname(local_dest_path), exist_ok=True)
    shutil.copyfile(LOCAL_MASTER_SKILL, local_dest_path)
    _inject_discovery_metadata(local_dest_path, agent_name, gcs_uri, endpoint)
    print(f"  ✓ Discovered skill compiled at: {local_dest_path}")
    return True


def discover_agents(project: str, location: str, output_dir: str, offline: bool = False):
    """
    Dispatches agent discovery query, parses descriptions, and syncs GCS skills.

    When `offline` is True, the network is never contacted: the demo agent card
    is used and skills are compiled from the local master source. This makes
    simulation mode deterministic instead of relying on a request failure.
    """
    agents = []
    if offline:
        print("🧪 Offline mode: skipping registry/GCS network calls; using localized agent card metadata...", flush=True)
        agents = [_demo_card(project, location)]
    else:
        print(f"🔍 Contacting Google Cloud Agent Registry in project: {project}, location: {location}...", flush=True)

        token = get_auth_token()
        url = f"https://agentregistry.googleapis.com/v1alpha/projects/{project}/locations/{location}/agents"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = httpx.get(url, headers=headers, timeout=20.0)
            if response.status_code == 200:
                agents = response.json().get("agents", [])
                print(f"Found {len(agents)} active agents in the registry.")

                # Ensure our demo agent card is always present for walkthrough compatibility
                has_demo = any("knowledge-catalog-agent" in (a.get("displayName") or a.get("name", "")) for a in agents)
                if not has_demo:
                    agents.append(_demo_card(project, location))
            else:
                print(f"Registry endpoint returned status: {response.status_code}. Using local demo fallback...", file=sys.stderr)
                raise Exception("Fallback to mock data")
        except Exception:
            # Fallback Mock Data for demo resilience
            print("💡 Simulation Mode: Using localized agent card metadata...")
            agents = [_demo_card(project, location)]

    # Patterns to extract the two card pointers:
    #   [SKILL_URI:gs://...]   → where the remote SKILL.md lives
    #   [AGENT_URI:https://...] → the reachable A2A/query endpoint for the agent
    skill_uri_pattern = re.compile(r"\[SKILL_URI:(gs://[^\]]+)\]")
    agent_uri_pattern = re.compile(r"\[AGENT_URI:(https://[^\]]+)\]")

    for agent in agents:
        agent_name = agent.get("displayName") or agent.get("name", "").split("/")[-1]
        card = agent.get("jsonAgentCard", {})
        description = card.get("description", "")

        match = skill_uri_pattern.search(description)
        if not match:
            continue

        gcs_uri = match.group(1)
        # Resolve the reachable endpoint from the card, falling back to the
        # locally deployed runtime recorded in deployment_metadata.json.
        endpoint_match = agent_uri_pattern.search(description)
        endpoint = endpoint_match.group(1) if endpoint_match else load_deployed_endpoint()

        print(f"\n🌟 Discovered Agent: {agent_name}")
        print(f"  Found Skill GCS URI: {gcs_uri}")
        print(f"  Resolved Endpoint:   {endpoint or '(none — endpoint not advertised)'}")

        local_dest_path = os.path.join(output_dir, agent_name, "SKILL.md")

        if offline:
            _compile_from_local_master(local_dest_path, agent_name, gcs_uri, endpoint)
            continue

        try:
            download_gcs_file(gcs_uri, local_dest_path)
            _inject_discovery_metadata(local_dest_path, agent_name, gcs_uri, endpoint)
        except Exception as e:
            print(f"  ⚠️  GCS download unavailable ({str(e)}).", file=sys.stderr)
            _compile_from_local_master(local_dest_path, agent_name, gcs_uri, endpoint)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize skills from the Google Cloud Agent Registry.")
    parser.add_argument("--project", default="<PROJECT_ID>", help="Google Cloud Project ID")
    parser.add_argument("--location", default="us-central1", help="GCP Region/Location")
    parser.add_argument("--output-dir", default="./skills/discovered", help="Local skills directory target")
    parser.add_argument("--offline", "--simulate", action="store_true", dest="offline",
                        help="Force simulation mode: skip all registry/GCS network calls and compile skills from local sources.")

    args = parser.parse_args()
    discover_agents(args.project, args.location, args.output_dir, offline=args.offline)
