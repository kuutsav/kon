import shutil
import sys
import tomllib
from contextvars import ContextVar
from copy import deepcopy
from importlib import resources
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

CONFIG_DIR_NAME: str = ".kon"

OnOverflowMode = Literal["continue", "pause"]


def _load_default_config_text() -> str:
    return resources.files("kon.defaults").joinpath("config.toml").read_text(encoding="utf-8")


_DEFAULT_CONFIG_DATA = tomllib.loads(_load_default_config_text())

_config_var: ContextVar["Config | None"] = ContextVar("kon_config", default=None)
_config_warnings: list[str] = []


class ToolBgConfig(BaseModel):
    pending: str
    success: str
    error: str


class CompactionBgConfig(BaseModel):
    bg: str
    label: str


class ColorsConfig(BaseModel):
    dim: str
    title: str
    spinner: str
    accent: str
    markdown_code: str
    selected: str
    error: str
    warning: str
    diff_added: str
    diff_removed: str
    tool_bg: ToolBgConfig
    compaction: CompactionBgConfig


class UIConfig(BaseModel):
    colors: ColorsConfig


class LLMConfig(BaseModel):
    default_provider: str
    default_model: str
    default_thinking_level: str
    system_prompt: str
    tool_call_idle_timeout_seconds: float = 60


class CompactionConfig(BaseModel):
    on_overflow: OnOverflowMode = "continue"
    buffer_tokens: int = 20000


class AgentConfig(BaseModel):
    max_turns: int = 500
    default_context_window: int = 200000


class ConfigSchema(BaseModel):
    llm: LLMConfig
    ui: UIConfig
    compaction: CompactionConfig
    agent: AgentConfig


class _BinariesConfig:
    def __init__(self, binaries: set[str]) -> None:
        self._binaries = binaries

    def has(self, binary: str) -> bool:
        return binary in self._binaries

    @property
    def rg(self) -> bool:
        return "rg" in self._binaries

    @property
    def fd(self) -> bool:
        return "fd" in self._binaries

    @property
    def eza(self) -> bool:
        return "eza" in self._binaries


class Config:
    def __init__(self, data: dict[str, Any]) -> None:
        merged = self.merge_with_defaults(data)
        self._parsed = ConfigSchema.model_validate(merged)

    @staticmethod
    def deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(base)
        for key, value in overrides.items():
            current_value = merged.get(key)
            if isinstance(current_value, dict) and isinstance(value, dict):
                merged[key] = Config.deep_merge(current_value, value)
            else:
                merged[key] = deepcopy(value)
        return merged

    @staticmethod
    def merge_with_defaults(data: dict[str, Any]) -> dict[str, Any]:
        return Config.deep_merge(_DEFAULT_CONFIG_DATA, data)

    @property
    def llm(self) -> LLMConfig:
        return self._parsed.llm

    @property
    def ui(self) -> UIConfig:
        return self._parsed.ui

    @property
    def compaction(self) -> CompactionConfig:
        return self._parsed.compaction

    @property
    def agent(self) -> AgentConfig:
        return self._parsed.agent

    @property
    def binaries(self) -> _BinariesConfig:
        return _BinariesConfig(AVAILABLE_BINARIES)


def get_config_dir() -> Path:
    return Path.home() / CONFIG_DIR_NAME


def _ensure_config_file() -> Path:
    config_dir = get_config_dir()
    config_file = config_dir / "config.toml"

    if not config_file.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(_load_default_config_text(), encoding="utf-8")

    return config_file


def _record_config_warning(message: str) -> None:
    _config_warnings.append(message)
    print(message, file=sys.stderr)


def consume_config_warnings() -> list[str]:
    warnings = _config_warnings.copy()
    _config_warnings.clear()
    return warnings


def _detect_available_binaries() -> set[str]:
    binaries = {"rg", "fd", "eza"}
    available = set()
    bin_dir = Path.home() / CONFIG_DIR_NAME / "bin"

    for binary in binaries:
        if shutil.which(binary) or (bin_dir / binary).exists():
            available.add(binary)

    return available


AVAILABLE_BINARIES = _detect_available_binaries()


def update_available_binaries() -> None:
    AVAILABLE_BINARIES.clear()
    AVAILABLE_BINARIES.update(_detect_available_binaries())


def _load_config() -> Config:
    config_file = _ensure_config_file()

    try:
        data = tomllib.loads(config_file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        _record_config_warning(
            f"Invalid config at {config_file}: {exc}. Falling back to built-in defaults."
        )
        data = {}

    try:
        return Config(data)
    except ValidationError as exc:
        _record_config_warning(
            f"Invalid config values at {config_file}: {exc}. Falling back to built-in defaults."
        )
        return Config({})


def get_config() -> Config:
    """
    Get the current config instance.

    Returns the config from context variable if set, otherwise loads from file.
    The loaded config is cached in the context variable.
    """
    cfg = _config_var.get()
    if cfg is None:
        cfg = _load_config()
        _config_var.set(cfg)
    return cfg


def set_config(config: Config) -> None:
    """Set the config instance (useful for testing)."""
    _config_var.set(config)


def reload_config() -> Config:
    """Reload config from file and update the context variable."""
    cfg = _load_config()
    _config_var.set(cfg)
    return cfg


def reset_config() -> None:
    """Reset config to uninitialized state (next get_config() will reload from file)."""
    _config_var.set(None)
    _config_warnings.clear()
