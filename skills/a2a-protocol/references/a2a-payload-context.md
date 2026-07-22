# A2A JSON-RPC Payload Reference Specs

This document outlines the detailed JSON schema structure and Python code templates required to communicate via the A2A protocol.

---

## 1. Full JSON-RPC A2A Request Schema (`message/send`)

Submit the following JSON payload inside the `input` field of the Vertex AI Reasoning Engine query POST request:

```json
{
  "jsonrpc": "2.0",
  "id": "req-17839420-a",
  "method": "message/send",
  "params": {
    "contextId": "1745646439066763264",
    "message": {
      "role": "user",
      "parts": [
        {
          "text": "What is my most successful campaign in the catalog?"
        },
        {
          "data": {
            "user_id": "admin@erantal.altostrat.com",
            "user_access_token": "ya29.a0AT3oNZ_..."
          }
        }
      ]
    }
  }
}
```

---

## 2. Full JSON-RPC A2A Response Schema

```json
{
  "jsonrpc": "2.0",
  "id": "req-17839420-a",
  "result": {
    "contextId": "1745646439066763264",
    "message": {
      "role": "model",
      "parts": [
        {
          "text": "Your top-performing campaign is 'tlv-summit-2026' with 4.5x ROAS."
        }
      ]
    },
    "artifacts": [
      {
        "id": "artifact-chart-001",
        "type": "image/png",
        "uri": "gs://tlv-2026-summit-agentscli-assets/charts/campaign_roi.png"
      }
    ]
  }
}
```

---

## 3. Python A2A Request Dispatcher

```python
import httpx

def send_a2a_message(endpoint_url: str, token: str, prompt: str, user_id: str, session_id: str = None) -> dict:
    """
    Constructs and dispatches an A2A JSON-RPC request to the target engine.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Compose Parts
    parts = [{"text": prompt}]
    if user_id and token:
        parts.append({
            "data": {
                "user_id": user_id,
                "user_access_token": token
            }
        })

    # 2. Structure Payload
    a2a_payload = {
        "jsonrpc": "2.0",
        "id": "msg-unique-abc",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": parts
            }
        }
    }
    
    if session_id:
        a2a_payload["params"]["contextId"] = session_id

    # 3. Dispatch to Vertex AI Agent Runtime
    response = httpx.post(
        endpoint_url,
        json={"class_method": "query", "input": a2a_payload},
        headers=headers,
        timeout=60.0
    )
    return response.json()
```
