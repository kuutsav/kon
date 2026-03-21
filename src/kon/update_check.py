import aiohttp


def _semver_tuple(version: str) -> tuple[int, int, int] | None:
    """Parse Kon versions that follow numeric semantic versioning.

    Update checks intentionally only support `MAJOR.MINOR.PATCH` versions
    such as `0.2.7` or `0.3.0`. If Kon's release versioning changes, this parser
    and the comparison logic in this module should be updated to match the new scheme.
    """
    parts = version.strip().split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


def is_newer_version(current_version: str, latest_version: str) -> bool:
    current_tuple = _semver_tuple(current_version)
    latest_tuple = _semver_tuple(latest_version)
    if current_tuple is None or latest_tuple is None:
        return False
    return latest_tuple > current_tuple


async def fetch_latest_pypi_version(package_name: str, timeout_seconds: float = 4.0) -> str | None:
    url = f"https://pypi.org/pypi/{package_name}/json"
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(url, headers={"User-Agent": "kon"}) as response,
        ):
            if response.status != 200:
                return None
            payload = await response.json(content_type=None)
    except Exception:
        return None

    info = payload.get("info") if isinstance(payload, dict) else None
    version = info.get("version") if isinstance(info, dict) else None
    return version if isinstance(version, str) and version.strip() else None


async def get_newer_pypi_version(package_name: str, current_version: str) -> str | None:
    latest_version = await fetch_latest_pypi_version(package_name)
    if latest_version is None:
        return None
    return latest_version if is_newer_version(current_version, latest_version) else None
