from kon.core.types import Message, ToolDefinition
from kon.llm.base import BaseProvider, LLMStream, ProviderConfig
from kon.llm.models import ApiType, get_model
from kon.runtime import ConversationRuntime


class _FakeProvider(BaseProvider):
    name = "fake"

    async def _stream_impl(
        self,
        messages: list[Message],
        *,
        system_prompt: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMStream:
        return LLMStream()

    def should_retry_for_error(self, error: Exception) -> bool:
        return False


def _runtime_with_provider(provider: BaseProvider) -> ConversationRuntime:
    runtime = ConversationRuntime(
        cwd="/test/project",
        model=provider.config.model,
        model_provider=provider.config.provider,
        api_key="test-key",
        base_url=None,
        thinking_level="high",
        tools=[],
    )
    runtime.provider = provider
    return runtime


def test_switch_model_recreates_provider_when_openai_compatible_base_url_changes(monkeypatch):
    initial_provider = _FakeProvider(
        ProviderConfig(
            provider="zhipu", base_url="https://api.z.ai/api/coding/paas/v4", model="glm-4.7"
        )
    )
    runtime = _runtime_with_provider(initial_provider)
    target = get_model("deepseek-v4-flash", "deepseek")
    assert target is not None

    created_configs: list[ProviderConfig] = []

    def fake_create_provider(api_type: ApiType, config: ProviderConfig) -> BaseProvider:
        assert api_type == ApiType.OPENAI_COMPLETIONS
        created_configs.append(config)
        return _FakeProvider(config)

    monkeypatch.setattr("kon.runtime.create_provider", fake_create_provider)

    runtime.switch_model(target)

    assert len(created_configs) == 1
    assert runtime.provider is not initial_provider
    assert runtime.provider is not None
    assert runtime.provider.config.provider == "deepseek"
    assert runtime.provider.config.base_url == "https://api.deepseek.com"
    assert runtime.provider.config.model == "deepseek-v4-flash"
    assert runtime.model == "deepseek-v4-flash"
    assert runtime.model_provider == "deepseek"


def test_switch_model_reuses_provider_when_openai_compatible_base_url_is_unchanged(monkeypatch):
    initial_provider = _FakeProvider(
        ProviderConfig(
            provider="deepseek", base_url="https://api.deepseek.com", model="deepseek-v4-pro"
        )
    )
    runtime = _runtime_with_provider(initial_provider)
    target = get_model("deepseek-v4-flash", "deepseek")
    assert target is not None

    def fail_create_provider(api_type: ApiType, config: ProviderConfig) -> BaseProvider:
        raise AssertionError("provider should not be recreated")

    monkeypatch.setattr("kon.runtime.create_provider", fail_create_provider)

    runtime.switch_model(target)

    assert runtime.provider is initial_provider
    provider = runtime.provider
    assert provider is not None
    assert provider.config.provider == "deepseek"
    assert provider.config.base_url == "https://api.deepseek.com"
    assert provider.config.model == "deepseek-v4-flash"
