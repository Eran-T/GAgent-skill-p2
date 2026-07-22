import os
import json
from typing import Dict, Any, Generator
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini

# ==============================================================================
# 🤖 Component 1: Knowledge Catalog Agent & A2A Server Wrap
# Deployed URN: projects/<PROJECT_NUMBER>/locations/<LOCATION>/reasoningEngines/<ENGINE_ID>
# Registered Agent Card:
#   Name: knowledge-catalog-agent
#   Description: Deployed Dataplex Catalog exploration engine.
#                [SKILL_URI:gs://<BUCKET_NAME>/skills/knowledge-catalog/SKILL.md]
# ==============================================================================

from google.adk.integrations.bigquery import BigQueryToolset

# Initialize high-performance standard model
gemini_model = Gemini(
    model_name="gemini-2.5-flash",
    temperature=0.0,
    client_kwargs={"vertexai": True}
)

# Instantiate google-adk Agent with native BigQuery/Dataplex Catalog Toolset
catalog_agent = Agent(
    name="knowledge_catalog_agent",
    instruction=(
        "You are an AI data steward connected directly to the Google Cloud Dataplex "
        "Knowledge Catalog. Your primary duty is to locate datasets, verify schemas, "
        "and retrieve tables metadata. Maintain deep analytical focus."
    ),
    model=gemini_model,
    tools=[
        BigQueryToolset()
    ]
)

from google.oauth2.credentials import Credentials
from google.adk.integrations.bigquery import BigQueryCredentialsConfig
from google.adk.runners import InMemoryRunner, types

# Standard ADK App instance
app = App(
    name="knowledge_catalog_app",
    root_agent=catalog_agent
)


class A2AServerWrapper:
    """
    Implements a JSON-RPC 2.0 A2A (Agent-to-Agent) compliance wrapper
    to execute structured requests on Agent Runtime.
    """

    def handle_a2a_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses A2A message/send requests, executes the reasoning model,
        and returns standardized JSON-RPC responses.
        """
        # 1. Validate JSON-RPC structure
        if payload.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: Must be JSON-RPC 2.0"},
                "id": payload.get("id")
            }

        method = payload.get("method")
        params = payload.get("params", {})
        msg_id = payload.get("id")

        if method != "message/send":
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": msg_id
            }

        # 2. Extract context parameters and thread history
        context_id = params.get("contextId")
        message_body = params.get("message", {})
        parts = message_body.get("parts", [])

        # Extract textual prompt and credential metadata
        prompt = ""
        user_id = ""
        user_access_token = ""

        for part in parts:
            if "text" in part:
                prompt = part["text"]
            elif "data" in part:
                data_block = part["data"]
                user_id = data_block.get("user_id", "")
                user_access_token = data_block.get("user_access_token", "")

        # 3. Dynamic authentication context mapping
        creds = None
        if user_access_token:
            # Set the credential in the environment for downstream Google APIs to consume
            os.environ["GOOGLE_OAUTH_ACCESS_TOKEN"] = user_access_token
            creds = Credentials(token=user_access_token)
        elif os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN"):
            creds = Credentials(token=os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN"))

        if creds:
            catalog_agent.model.client_kwargs["credentials"] = creds
            creds_config = BigQueryCredentialsConfig(credentials=creds)
            catalog_agent.tools = [BigQueryToolset(credentials_config=creds_config)]
        else:
            catalog_agent.tools = [BigQueryToolset()]

        # 4. Invoke agent model
        try:
            # Execute standard adk App invocation via InMemoryRunner
            runner = InMemoryRunner(app=app)
            runner.auto_create_session = True

            msg = types.Content(role="user", parts=[types.Part(text=prompt)])
            events = runner.run(
                user_id=user_id or "user-default",
                session_id=context_id or "session-default",
                new_message=msg
            )

            final_text = ""
            for event in events:
                if hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_text += part.text

            # 5. Build A2A compliant JSON-RPC response
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "contextId": context_id or "session-temp-123",
                    "message": {
                        "role": "model",
                        "parts": [
                            {"kind": "text", "text": final_text}
                        ]
                    },
                    "artifacts": []
                }
            }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal Server Error: {str(e)}"},
                "id": msg_id
            }


# Entrypoint class conforming to Vertex AI Reasoning Engine serialization standards
class KnowledgeCatalogEngine:
    def __init__(self):
        self.server = A2AServerWrapper()

    def query(self, class_method: str, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vertex AI Agent Runtime dispatch hook.
        """
        return self.server.handle_a2a_request(input)

    def stream_query(self, message: str, user_id: str, session_id: str = None) -> Generator[Dict[str, Any], None, None]:
        """
        Standard streaming route.
        """
        runner = InMemoryRunner(app=app)
        runner.auto_create_session = True

        msg = types.Content(role="user", parts=[types.Part(text=message)])
        events = runner.run(
            user_id=user_id or "user-default",
            session_id=session_id or "session-default",
            new_message=msg
        )

        for event in events:
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        yield {"chunk": part.text}

# Concrete instance conforming to Vertex AI Agent Runtime execution standards
agent_runtime = KnowledgeCatalogEngine()
