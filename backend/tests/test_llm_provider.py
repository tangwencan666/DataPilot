from types import SimpleNamespace

import httpx
import openai
import pytest
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.exceptions import LLMInvalidResponseError, LLMProviderError
from app.query import provider as provider_module
from app.query.provider import OpenAICompatibleProvider


class SmokeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class FakeClient:
    def __init__(self, *, chat_content='{"status":"CHAT_OK"}', response_content='{"status":"RESPONSES_OK"}', error=None):
        self.chat_calls = []
        self.response_calls = []
        self._chat_content = chat_content
        self._response_content = response_content
        self._error = error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat_create))
        self.responses = SimpleNamespace(create=self._response_create)

    def _chat_create(self, **kwargs):
        self.chat_calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self._chat_content))])

    def _response_create(self, **kwargs):
        self.response_calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(output_text=self._response_content)


def make_provider(monkeypatch, base_url: str, client: FakeClient) -> OpenAICompatibleProvider:
    monkeypatch.setattr(provider_module, "OpenAI", lambda **_: client)
    return OpenAICompatibleProvider(Settings(llm_api_key="test-secret", llm_model="test-model", llm_base_url=base_url))


def test_non_deepseek_structured_call_preserves_chat_completions(monkeypatch):
    client = FakeClient()
    provider = make_provider(monkeypatch, "https://api.openai.com/v1", client)

    result = provider._structured("Return JSON", "status", SmokeResult, "smoke_result")

    assert result.status == "CHAT_OK"
    assert len(client.chat_calls) == 1
    assert not client.response_calls
    response_format = client.chat_calls[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True


def test_deepseek_plain_chat_capability_does_not_change_structured_routing(monkeypatch):
    client = FakeClient()
    provider = make_provider(monkeypatch, "https://api.deepseek.com", client)

    assert provider.is_configured is True
    assert provider._uses_responses_structured_output is True
    assert not client.chat_calls
    assert not client.response_calls


def test_deepseek_structured_call_uses_responses_json_schema(monkeypatch):
    client = FakeClient()
    provider = make_provider(monkeypatch, "https://api.deepseek.com/v1", client)

    result = provider._structured("Return JSON", "status", SmokeResult, "smoke_result")

    assert result.status == "RESPONSES_OK"
    assert not client.chat_calls
    assert len(client.response_calls) == 1
    payload = client.response_calls[0]
    assert payload["text"]["format"] == {
        "type": "json_schema",
        "name": "smoke_result",
        "schema": SmokeResult.model_json_schema(),
    }
    assert payload["reasoning"] == {"effort": "low"}


def test_deepseek_structured_malformed_output_fails_safely(monkeypatch):
    provider = make_provider(monkeypatch, "https://api.deepseek.com", FakeClient(response_content="not-json"))

    with pytest.raises(LLMInvalidResponseError) as exc_info:
        provider._structured("Return JSON", "status", SmokeResult, "smoke_result")

    assert "invalid structured Agent response" in exc_info.value.detail
    assert "not-json" not in exc_info.value.detail


def test_deepseek_provider_error_is_mapped_without_secret(monkeypatch):
    request = httpx.Request("POST", "https://api.deepseek.com/responses")
    response = httpx.Response(400, request=request, json={"error": {"message": "unsupported format"}})
    error = openai.BadRequestError("unsupported format", response=response, body=response.json())
    provider = make_provider(monkeypatch, "https://api.deepseek.com", FakeClient(error=error))

    with pytest.raises(LLMProviderError) as exc_info:
        provider._structured("Return JSON", "status", SmokeResult, "smoke_result")

    assert exc_info.value.code == "LLM_PROVIDER_COMPATIBILITY_ERROR"
    assert exc_info.value.detail == "LLM provider rejected the structured request."
    assert "test-secret" not in exc_info.value.detail
