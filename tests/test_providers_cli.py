import json

import httpx
import pytest

from myagent.cli import main
from myagent.models import Decision
from myagent.providers import ProviderError, RemoteModel


@pytest.mark.parametrize("provider", ["ollama", "openai"])
def test_remote_model_protocol(provider):
    def handler(request):
        payload = json.loads(request.content)
        assert payload["stream"] is False and payload["model"] == "test-model"
        assert request.headers["authorization"] == "Bearer fake-key"
        assert "untrusted" in payload["messages"][0]["content"]
        answer = json.dumps({"complete": True, "summary": "Inspected sources."})
        if provider == "ollama":
            assert request.url.path == "/api/chat" and "properties" in payload["format"]
            return httpx.Response(
                200, json={"message": {"content": answer, "thinking": "not returned or logged"}}
            )
        assert request.url.path == "/v1/chat/completions" and payload["response_format"] == {
            "type": "json_object"
        }
        return httpx.Response(200, json={"choices": [{"message": {"content": answer}}]})

    model = RemoteModel(
        provider,
        "test-model",
        "http://test/v1" if provider == "openai" else "http://test",
        "fake-key",
        httpx.MockTransport(handler),
    )
    assert model.complete("act", {"task": "test"}, Decision.model_json_schema())["complete"]


@pytest.mark.parametrize(
    "body",
    [{}, {"message": {"content": "not json"}}, {"message": {"content": "[]"}}, {"message": None}],
)
def test_malformed_model_response_fails(body):
    model = RemoteModel(
        "ollama",
        "test",
        "http://test",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    )
    with pytest.raises(ProviderError):
        model.complete("act", {}, {})


def test_http_error_does_not_expose_secret_response():
    model = RemoteModel(
        "ollama",
        "test",
        "http://test",
        transport=httpx.MockTransport(lambda request: httpx.Response(401, text="private-response")),
    )
    with pytest.raises(ProviderError) as error:
        model.complete("act", {}, {})
    assert "private-response" not in str(error.value)


def test_cli_demo_show_and_undo(tmp_path, capsys):
    assert main(["demo", "--workspace", str(tmp_path), "--json"]) == 0
    run = json.loads(capsys.readouterr().out)
    assert run["status"] == "succeeded"
    assert main(["show", run["id"], "--workspace", str(tmp_path), "--json"]) == 0
    detail = json.loads(capsys.readouterr().out)
    assert detail["events"] and len(detail["changes"]) == 2
    assert main(["demo", "--workspace", str(tmp_path)]) == 1
    assert main(["undo", run["id"], "--workspace", str(tmp_path)]) == 0
    assert not (tmp_path / "temperatures.py").exists()


def test_missing_model_fails_without_tool_execution(tmp_path, monkeypatch):
    monkeypatch.delenv("MYAGENT_MODEL", raising=False)
    assert main(["run", "Create a file", "--workspace", str(tmp_path), "--model", ""]) == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == [".myagent"]
