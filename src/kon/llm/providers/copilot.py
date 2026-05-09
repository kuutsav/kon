"""
GitHub Copilot provider.

Uses the OpenAI-compatible API with Copilot-specific headers and OAuth tokens.
"""

from openai import AsyncOpenAI

from ...core.types import Message, ToolDefinition
from ..base import BaseProvider, LLMStream, ProviderConfig
from ..oauth import COPILOT_HEADERS, get_base_url_from_token, get_valid_token, load_credentials
from .github_copilot_headers import build_copilot_dynamic_headers
from .openai_completions import OpenAICompletionsProvider
from .openai_responses import OpenAIResponsesProvider


class CopilotProvider(OpenAICompletionsProvider):
    """
    GitHub Copilot provider.

    Inherits from OpenAIProvider since Copilot uses an OpenAI-compatible API,
    but adds Copilot-specific headers and OAuth token management.

    Note: Copilot enables thinking for Claude models server-side automatically.
    We don't send reasoning_effort - just read thinking from reasoning_content in responses.
    """

    name = "github-copilot"
    thinking_levels: list[str] = ["none", "minimal", "low", "medium", "high", "xhigh"]  # noqa: RUF012
    # Copilot doesn't accept reasoning_effort - thinking is enabled server-side
    supports_reasoning_effort: bool = False
    # Copilot requires assistant content as string, not array.
    # Sending as array causes Claude models to re-answer all previous prompts.
    force_string_assistant_content: bool = True

    def __init__(self, config: ProviderConfig):
        # Skip OpenAIProvider.__init__ since we need custom client setup
        BaseProvider.__init__(self, config)

        # We'll initialize the client lazily when we have a valid token
        self._client: AsyncOpenAI | None = None
        self._current_token: str | None = None

    async def _ensure_client(self) -> AsyncOpenAI:
        token = await get_valid_token()
        if not token:
            raise RuntimeError("Not logged in to GitHub Copilot. Use /login to authenticate.")

        # Recreate client if token changed
        if token != self._current_token or self._client is None:
            self._current_token = token
            creds = load_credentials()
            base_url = get_base_url_from_token(token, creds.enterprise_domain if creds else None)
            self._client = AsyncOpenAI(
                api_key=token, base_url=base_url, default_headers=COPILOT_HEADERS
            )

        return self._client

    async def stream(
        self,
        messages: list[Message],
        *,
        system_prompt: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMStream:
        self._client = await self._ensure_client()
        dynamic_headers = build_copilot_dynamic_headers(messages)
        self._client = AsyncOpenAI(
            api_key=self._current_token,
            base_url=str(self._client.base_url),
            default_headers={**COPILOT_HEADERS, **dynamic_headers},
        )
        return await super()._stream_impl(
            messages,
            system_prompt=system_prompt,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )


class CopilotResponsesProvider(OpenAIResponsesProvider):
    """
    GitHub Copilot provider for OpenAI Responses API (GPT-5, Codex models).

    Inherits from OpenAIResponsesProvider but adds Copilot-specific
    headers and OAuth token management.
    """

    name = "github-copilot"

    def __init__(self, config: ProviderConfig):
        # Skip parent __init__ since we need custom client setup
        BaseProvider.__init__(self, config)
        self._headers = COPILOT_HEADERS.copy()
        self._client: AsyncOpenAI | None = None
        self._current_token: str | None = None

    async def _ensure_client(self) -> AsyncOpenAI:
        token = await get_valid_token()
        if not token:
            raise RuntimeError("Not logged in to GitHub Copilot. Use /login to authenticate.")

        if token != self._current_token or self._client is None:
            self._current_token = token
            creds = load_credentials()
            base_url = get_base_url_from_token(token, creds.enterprise_domain if creds else None)
            self._client = AsyncOpenAI(
                api_key=token, base_url=base_url, default_headers=self._headers
            )

        return self._client

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            raise RuntimeError("Client not initialized. Call _ensure_client first.")
        return self._client

    async def stream(
        self,
        messages: list[Message],
        *,
        system_prompt: str | None = None,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMStream:
        self._client = await self._ensure_client()
        dynamic_headers = build_copilot_dynamic_headers(messages)
        self._client = AsyncOpenAI(
            api_key=self._current_token,
            base_url=str(self._client.base_url),
            default_headers={**COPILOT_HEADERS, **dynamic_headers},
        )
        return await super()._stream_impl(
            messages,
            system_prompt=system_prompt,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
