# GCP Authentication Command Reference

This reference outlines the exact shell commands and Python snippets utilized to authorize and retrieve Google Cloud access tokens.

---

## 1. Programmatic Token Retrieval (Python)

To retrieve active Google Cloud Application Default Credentials (ADC) tokens in Python without relying on subprocess shell calls:

```python
import google.auth
import google.auth.transport.requests

def get_active_access_token() -> str:
    """
    Retrieves the active Google Cloud OAuth2 access token programmatically.
    """
    # Load default application credentials
    credentials, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    
    # Refresh token if necessary
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    
    return credentials.token
```

---

## 2. Shell Commands & Environment Mapping

*   **Initialize Application Default Credentials (ADC):**
    ```bash
    gcloud auth application-default login
    ```
    This generates a JSON file locally at:
    *   **macOS/Linux:** `~/.config/gcloud/application_default_credentials.json`
    *   **Windows:** `%APPDATA%\gcloud\application_default_credentials.json`

*   **Generate Access Token:**
    ```bash
    gcloud auth print-access-token
    ```

*   **Target Cloud Project Environment Variable:**
    ```bash
    export GOOGLE_CLOUD_PROJECT="bigquery-demo-430909"
    ```
