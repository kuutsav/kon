"""
GitHub Copilot OAuth device flow.

Implements the device code flow to authenticate with GitHub and
exchange for a Copilot token that can be used with the Copilot API.
"""

import asyncio
import json
from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp

# GitHub OAuth client ID (same as VS Code Copilot extension)
_CLIENT_ID = b64decode("SXYxLmI1MDdhMDhjODdlY2ZlOTg=").decode()

# Required headers for Copilot API
COPILOT_HEADERS = {
    "User-Agent": "GitHubCopilotChat/0.35.0",
    "Editor-Version": "vscode/1.107.0",
    "Editor-Plugin-Version": "copilot-chat/0.35.0",
    "Copilot-Integration-Id": "vscode-chat",
}


@dataclass
class CopilotCredentials:
    github_token: str  # Long-lived GitHub OAuth token (refresh token)
    copilot_token: str  # Short-lived Copilot API token (access token)
    expires_at: int  # Unix timestamp (milliseconds) when copilot_token expires
    enterprise_domain: str | None = None  # For GitHub Enterprise


@dataclass
class DeviceCodeResponse:
    device_code: str
    user_code: str
    verification_uri: str
    interval: int
    expires_in: int


def get_copilot_auth_path() -> Path:
    return Path.home() / ".kon" / "copilot_auth.json"


def load_credentials() -> CopilotCredentials | None:
    path = get_copilot_auth_path()
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
        return CopilotCredentials(
            github_token=data["github_token"],
            copilot_token=data["copilot_token"],
            expires_at=data["expires_at"],
            enterprise_domain=data.get("enterprise_domain"),
        )
    except (json.JSONDecodeError, KeyError):
        return None


def save_credentials(creds: CopilotCredentials) -> None:
    path = get_copilot_auth_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "github_token": creds.github_token,
        "copilot_token": creds.copilot_token,
        "expires_at": creds.expires_at,
    }
    if creds.enterprise_domain:
        data["enterprise_domain"] = creds.enterprise_domain

    path.write_text(json.dumps(data, indent=2))
    path.chmod(0o600)


def clear_credentials() -> None:
    path = get_copilot_auth_path()
    if path.exists():
        path.unlink()


def is_copilot_logged_in() -> bool:
    return load_credentials() is not None


def _get_urls(domain: str) -> dict[str, str]:
    return {
        "device_code": f"https://{domain}/login/device/code",
        "access_token": f"https://{domain}/login/oauth/access_token",
        "copilot_token": f"https://api.{domain}/copilot_internal/v2/token",
    }


def get_base_url_from_token(token: str, enterprise_domain: str | None = None) -> str:
    """
    Extract API base URL from Copilot token.

    Token format: tid=...;exp=...;proxy-ep=proxy.individual.githubcopilot.com;...
    Returns API URL like https://api.individual.githubcopilot.com
    """
    import re

    match = re.search(r"proxy-ep=([^;]+)", token)
    if match:
        proxy_host = match.group(1)
        api_host = proxy_host.replace("proxy.", "api.", 1)
        return f"https://{api_host}"

    # Fallback
    if enterprise_domain:
        return f"https://copilot-api.{enterprise_domain}"
    return "https://api.individual.githubcopilot.com"


async def start_device_flow(domain: str = "github.com") -> DeviceCodeResponse:
    urls = _get_urls(domain)

    async with (
        aiohttp.ClientSession() as session,
        session.post(
            urls["device_code"],
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "GitHubCopilotChat/0.35.0",
            },
            json={"client_id": _CLIENT_ID, "scope": "read:user"},
        ) as response,
    ):
        response.raise_for_status()
        data = await response.json()

    return DeviceCodeResponse(
        device_code=data["device_code"],
        user_code=data["user_code"],
        verification_uri=data["verification_uri"],
        interval=data["interval"],
        expires_in=data["expires_in"],
    )


async def poll_for_github_token(
    device_code: str,
    interval: int,
    expires_in: int,
    domain: str = "github.com",
    on_poll: Any | None = None,
) -> str:
    """
    Poll GitHub for the access token after user authorizes.

    Returns the GitHub OAuth access token.
    Raises TimeoutError if the flow expires.
    """
    import time

    urls = _get_urls(domain)
    deadline = time.time() + expires_in
    poll_interval = max(1, interval)

    async with aiohttp.ClientSession() as session:
        while time.time() < deadline:
            if on_poll:
                on_poll()

            async with session.post(
                urls["access_token"],
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "GitHubCopilotChat/0.35.0",
                },
                json={
                    "client_id": _CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            ) as response:
                data = await response.json()

            if "access_token" in data:
                return data["access_token"]

            error = data.get("error")
            if error == "authorization_pending":
                await asyncio.sleep(poll_interval)
                continue
            elif error == "slow_down":
                poll_interval += 5
                await asyncio.sleep(poll_interval)
                continue
            elif error == "expired_token":
                raise TimeoutError("Device code expired")
            else:
                raise RuntimeError(f"OAuth error: {error}")

    raise TimeoutError("Device code flow timed out")


async def exchange_for_copilot_token(
    github_token: str, domain: str = "github.com"
) -> tuple[str, int]:
    """
    Exchange GitHub OAuth token for Copilot API token.

    Returns (copilot_token, expires_at_ms).
    """
    urls = _get_urls(domain)

    async with (
        aiohttp.ClientSession() as session,
        session.get(
            urls["copilot_token"],
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {github_token}",
                **COPILOT_HEADERS,
            },
        ) as response,
    ):
        if response.status == 401:
            raise RuntimeError(
                "GitHub Copilot subscription not found. "
                "Make sure you have an active Copilot subscription."
            )
        response.raise_for_status()
        data = await response.json()

    token = data["token"]
    # expires_at is in seconds, convert to milliseconds with 5min buffer
    expires_at = data["expires_at"] * 1000 - 5 * 60 * 1000

    return token, expires_at


async def refresh_copilot_token(creds: CopilotCredentials) -> CopilotCredentials:
    domain = creds.enterprise_domain or "github.com"
    copilot_token, expires_at = await exchange_for_copilot_token(creds.github_token, domain)

    new_creds = CopilotCredentials(
        github_token=creds.github_token,
        copilot_token=copilot_token,
        expires_at=expires_at,
        enterprise_domain=creds.enterprise_domain,
    )
    save_credentials(new_creds)
    return new_creds


async def get_valid_token() -> str | None:
    """
    Get a valid Copilot API token, refreshing if needed.

    Returns None if not logged in.
    """
    import time

    creds = load_credentials()
    if not creds:
        return None

    # Check if token needs refresh (with 1 minute buffer)
    if time.time() * 1000 >= creds.expires_at - 60_000:
        try:
            creds = await refresh_copilot_token(creds)
        except Exception:
            # Token refresh failed, need to re-login
            return None

    return creds.copilot_token


async def _enable_copilot_model(
    token: str, model_id: str, enterprise_domain: str | None = None
) -> bool:
    base_url = get_base_url_from_token(token, enterprise_domain)
    url = f"{base_url}/models/{model_id}/policy"

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                    **COPILOT_HEADERS,
                    "openai-intent": "chat-policy",
                    "x-interaction-type": "chat-policy",
                },
                json={"state": "enabled"},
            ) as response,
        ):
            return response.status < 400
    except Exception:
        return False


async def enable_all_copilot_models(token: str, enterprise_domain: str | None = None) -> None:
    from ..models import MODELS

    copilot_models = [m for m in MODELS.values() if m.provider == "github-copilot"]
    tasks = [_enable_copilot_model(token, model.id, enterprise_domain) for model in copilot_models]
    await asyncio.gather(*tasks, return_exceptions=True)


async def login(
    on_user_code: Any | None = None, enterprise_domain: str | None = None
) -> CopilotCredentials:
    """
    Perform the full Copilot login flow.

    Args:
        on_user_code: Callback with (verification_uri, user_code) when user action needed
        enterprise_domain: Optional GitHub Enterprise domain

    Returns:
        CopilotCredentials that are saved and ready to use
    """
    domain = enterprise_domain or "github.com"

    # Start device flow
    device = await start_device_flow(domain)

    # Notify caller about user action needed
    if on_user_code:
        on_user_code(device.verification_uri, device.user_code)

    # Poll for GitHub token
    github_token = await poll_for_github_token(
        device.device_code, device.interval, device.expires_in, domain
    )

    # Exchange for Copilot token
    copilot_token, expires_at = await exchange_for_copilot_token(github_token, domain)

    # Save and return credentials
    creds = CopilotCredentials(
        github_token=github_token,
        copilot_token=copilot_token,
        expires_at=expires_at,
        enterprise_domain=enterprise_domain,
    )
    save_credentials(creds)

    # Enable all Copilot models (some require policy acceptance)
    await enable_all_copilot_models(copilot_token, enterprise_domain)

    return creds
