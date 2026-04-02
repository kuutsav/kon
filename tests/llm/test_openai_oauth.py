from unittest.mock import patch

import pytest

from kon.llm.oauth.openai import login


@pytest.mark.asyncio
async def test_login_raises_runtime_error_when_server_fails_and_no_manual_input():
    with (
        patch("kon.llm.oauth.openai._start_callback_server", side_effect=OSError("port in use")),
        pytest.raises(RuntimeError, match="could not start callback server"),
    ):
        await login(on_auth_url=None, on_manual_input=None)
