"""
Unit tests for the backend A2A server logic in `backend/agent.py`.

These tests exercise the pure request-parsing and response-shaping logic of the
Agent Runtime entrypoint WITHOUT requiring google-adk or any Google Cloud access.
The heavy ADK dependencies are replaced with lightweight stub modules before the
backend is imported, and the ADK runner is replaced with a fake that yields a
canned event. This keeps the JSON-RPC 2.0 A2A contract under test.

Run:
    python3 -m unittest backend.test_agent -v
    # or
    python3 backend/test_agent.py
"""
import os
import sys
import types as _pytypes
import unittest
from unittest import mock


def _install_adk_stubs():
    """
    Register minimal stub modules so `import backend.agent` succeeds without the
    real google-adk / google-cloud packages installed. Every stubbed symbol is a
    MagicMock, so constructors like Agent(...), App(...), Gemini(...) just return
    mocks. The runner is patched per-test to control emitted events.
    """
    def _mod(name):
        m = _pytypes.ModuleType(name)
        sys.modules[name] = m
        return m

    # google + google.adk package tree
    google = sys.modules.get("google") or _mod("google")
    _mod("google.adk")
    adk_agents = _mod("google.adk.agents")
    adk_agents.Agent = mock.MagicMock(name="Agent")
    adk_apps = _mod("google.adk.apps")
    adk_apps.App = mock.MagicMock(name="App")
    adk_models = _mod("google.adk.models")
    adk_models.Gemini = mock.MagicMock(name="Gemini")

    adk_integrations = _mod("google.adk.integrations")
    adk_bq = _mod("google.adk.integrations.bigquery")
    adk_bq.BigQueryToolset = mock.MagicMock(name="BigQueryToolset")
    adk_bq.BigQueryCredentialsConfig = mock.MagicMock(name="BigQueryCredentialsConfig")

    adk_runners = _mod("google.adk.runners")
    adk_runners.InMemoryRunner = mock.MagicMock(name="InMemoryRunner")
    adk_runners.types = mock.MagicMock(name="types")

    # google.oauth2.credentials.Credentials
    _mod("google.oauth2")
    oauth_creds = _mod("google.oauth2.credentials")
    oauth_creds.Credentials = mock.MagicMock(name="Credentials")

    return google


# Install stubs and import the backend once for the whole module.
_install_adk_stubs()
from backend import agent as backend_agent  # noqa: E402


class _FakePart:
    def __init__(self, text):
        self.text = text


class _FakeContent:
    def __init__(self, texts):
        self.parts = [_FakePart(t) for t in texts]


class _FakeEvent:
    def __init__(self, texts):
        self.content = _FakeContent(texts)


def _fake_runner_yielding(texts):
    """Returns a MagicMock InMemoryRunner whose .run() yields one fake event."""
    runner_instance = mock.MagicMock()
    runner_instance.run.return_value = iter([_FakeEvent(texts)])
    factory = mock.MagicMock(return_value=runner_instance)
    return factory, runner_instance


class A2ARequestTests(unittest.TestCase):
    def setUp(self):
        self.server = backend_agent.A2AServerWrapper()

    def _valid_payload(self, **overrides):
        payload = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "message/send",
            "params": {
                "contextId": "ctx-42",
                "message": {
                    "role": "user",
                    "parts": [
                        {"text": "find campaign tables"},
                        {"data": {"user_id": "u@example.com",
                                  "user_access_token": "tok-abc"}},
                    ],
                },
            },
        }
        payload.update(overrides)
        return payload

    def test_rejects_non_jsonrpc_2(self):
        resp = self.server.handle_a2a_request({"jsonrpc": "1.0", "id": "x"})
        self.assertEqual(resp["error"]["code"], -32600)
        self.assertEqual(resp["id"], "x")

    def test_rejects_unknown_method(self):
        resp = self.server.handle_a2a_request(
            {"jsonrpc": "2.0", "id": "y", "method": "message/stream"}
        )
        self.assertEqual(resp["error"]["code"], -32601)
        self.assertIn("message/stream", resp["error"]["message"])

    def test_happy_path_shapes_response_and_echoes_context(self):
        factory, _ = _fake_runner_yielding(["schema A ", "schema B"])
        with mock.patch.object(backend_agent, "InMemoryRunner", factory), \
             mock.patch.object(backend_agent, "_apply_delegated_credentials") as apply_creds:
            resp = self.server.handle_a2a_request(self._valid_payload())

        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], "req-1")
        self.assertEqual(resp["result"]["contextId"], "ctx-42")
        parts = resp["result"]["message"]["parts"]
        self.assertEqual(parts[0]["text"], "schema A schema B")
        self.assertEqual(resp["result"]["message"]["role"], "model")
        # delegated token from the DataPart must be forwarded to auth mapping
        apply_creds.assert_called_once_with("tok-abc")

    def test_default_context_when_missing(self):
        factory, _ = _fake_runner_yielding(["ok"])
        payload = self._valid_payload()
        del payload["params"]["contextId"]
        with mock.patch.object(backend_agent, "InMemoryRunner", factory), \
             mock.patch.object(backend_agent, "_apply_delegated_credentials"):
            resp = self.server.handle_a2a_request(payload)
        self.assertEqual(resp["result"]["contextId"], "session-temp-123")

    def test_runner_exception_becomes_jsonrpc_error(self):
        runner_instance = mock.MagicMock()
        runner_instance.run.side_effect = RuntimeError("boom")
        factory = mock.MagicMock(return_value=runner_instance)
        with mock.patch.object(backend_agent, "InMemoryRunner", factory), \
             mock.patch.object(backend_agent, "_apply_delegated_credentials"):
            resp = self.server.handle_a2a_request(self._valid_payload())
        self.assertEqual(resp["error"]["code"], -32603)
        self.assertIn("boom", resp["error"]["message"])


class StreamQueryTests(unittest.TestCase):
    def test_stream_query_yields_chunks_and_applies_delegated_auth(self):
        engine = backend_agent.KnowledgeCatalogEngine()
        factory, _ = _fake_runner_yielding(["chunk1", "chunk2"])
        with mock.patch.object(backend_agent, "InMemoryRunner", factory), \
             mock.patch.object(backend_agent, "_apply_delegated_credentials") as apply_creds:
            chunks = list(engine.stream_query(
                message="hi", user_id="u@example.com",
                session_id="s1", user_access_token="tok-xyz",
            ))
        self.assertEqual(chunks, [{"chunk": "chunk1"}, {"chunk": "chunk2"}])
        apply_creds.assert_called_once_with("tok-xyz")


class DelegatedCredentialTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("GOOGLE_OAUTH_ACCESS_TOKEN", None)

    def test_token_is_exported_to_environment(self):
        # Real function under test; ADK symbols are mocks so tool wiring is a no-op.
        backend_agent._apply_delegated_credentials("delegated-token-123")
        self.assertEqual(os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN"),
                         "delegated-token-123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
