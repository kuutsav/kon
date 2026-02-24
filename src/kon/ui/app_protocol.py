from typing import Any, Protocol

from ..llm import ApiType, BaseProvider, ProviderConfig
from ..session import Session
from .selection_mode import SelectionMode


class Kon(Protocol):
    """Protocol defining the interface expected by mixins."""

    # App-level attributes
    VERSION: str
    _cwd: str
    _model: str
    _api_key: str | None
    _base_url: str | None
    _thinking_level: str
    _hide_thinking: bool
    _selection_mode: SelectionMode | None
    _provider: BaseProvider | None
    _session: Session | None
    _agent: Any

    # Methods expected by mixins
    def exit(self) -> None: ...
    def query_one(self, selector: str) -> object: ...
    def notify(self, message: str, **kwargs: object) -> None: ...
    def run_worker(self, coro: object, exclusive: bool) -> None: ...
    def call_later(self, callback: object, message: str) -> None: ...

    # Methods expected by SessionUIMixin
    def _get_provider_api_type(self, provider: BaseProvider) -> ApiType: ...
    def _create_provider(self, api_type: ApiType, config: ProviderConfig) -> BaseProvider: ...
