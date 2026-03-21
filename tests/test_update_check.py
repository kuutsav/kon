import pytest

from kon.update_check import get_newer_pypi_version, is_newer_version


def test_is_newer_version_basic_semver_cases() -> None:
    assert is_newer_version("0.1.0", "0.1.1")
    assert is_newer_version("0.1.0", "0.2.0")
    assert not is_newer_version("0.2.0", "0.1.9")
    assert not is_newer_version("1.0.0", "1.0.0")


def test_is_newer_version_returns_false_for_non_semver_values() -> None:
    assert not is_newer_version("1.0.0rc1", "1.0.0")
    assert not is_newer_version("1.0.0", "1.0.0rc1")
    assert not is_newer_version("bad", "1.0.0")


@pytest.mark.asyncio
async def test_get_newer_pypi_version_returns_newer_value(monkeypatch) -> None:
    async def fake_fetch(package_name: str) -> str | None:
        assert package_name == "kon-coding-agent"
        return "9.9.9"

    monkeypatch.setattr("kon.update_check.fetch_latest_pypi_version", fake_fetch)

    result = await get_newer_pypi_version("kon-coding-agent", "0.1.0")
    assert result == "9.9.9"


@pytest.mark.asyncio
async def test_get_newer_pypi_version_returns_none_when_not_newer(monkeypatch) -> None:
    async def fake_fetch(_: str) -> str | None:
        return "0.1.0"

    monkeypatch.setattr("kon.update_check.fetch_latest_pypi_version", fake_fetch)

    result = await get_newer_pypi_version("kon-coding-agent", "0.1.0")
    assert result is None
