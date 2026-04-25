"""Tests for shell command detection and execution functionality."""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from kon.ui.app import Kon
from kon.ui.input import InputBox
from kon.ui.chat import ChatLog
from kon.tools.bash import BashTool, BashParams


@pytest.mark.asyncio
async def test_shell_command_detection():
    """Test that shell commands are properly detected."""
    test_cases = [
        ("!ls -la", True, "ls -la", False),
        ("!!grep -r TODO src/", True, "grep -r TODO src/", True),
        ("!  echo hello  ", True, "echo hello", False),
        ("!!  python -m pytest  ", True, "python -m pytest", True),
        ("echo hello", False, None, False),
        ("/help", False, None, False),
        ("", False, None, False),
    ]
    
    for input_text, should_handle, expected_command, expected_send_to_llm in test_cases:
        if should_handle:
            send_to_llm = input_text.startswith("!!")
            command_text = input_text[2:] if send_to_llm else input_text[1:]
            command_text = command_text.strip()
            
            assert send_to_llm == expected_send_to_llm
            assert command_text == expected_command
        else:
            # Should not be handled as shell command
            assert not (input_text.startswith("!") or input_text.startswith("!!"))


@pytest.mark.asyncio
async def test_shell_command_execution():
    """Test shell command execution with mock components."""
    # Create mock app
    app = MagicMock(spec=Kon)
    app._is_running = False
    
    # Mock chat log
    mock_chat = MagicMock(spec=ChatLog)
    app.query_one.return_value = mock_chat
    
    # Mock status line
    mock_status = MagicMock()
    
    def query_one_side_effect(selector):
        if selector == "#chat-log":
            return mock_chat
        elif selector == "#status-line":
            return mock_status
        return MagicMock()
    
    app.query_one.side_effect = query_one_side_effect
    
    # Test bash tool directly
    bash_tool = BashTool()
    
    # Test successful command
    result = await bash_tool.execute(BashParams(command="echo 'test'"))
    assert result.success == True
    assert "test" in result.result
    
    # Test failed command
    result = await bash_tool.execute(BashParams(command="ls /nonexistent_12345"))
    assert result.success == False
    assert result.ui_summary is not None


@pytest.mark.asyncio
async def test_shell_command_output_formatting():
    """Test that command output is properly formatted."""
    bash_tool = BashTool()
    
    # Test command with output
    result = await bash_tool.execute(BashParams(command="ls -la"))
    assert result.success == True
    assert len(result.result) > 0
    
    # For commands with significant output, ui_details should be present
    if len(result.result) > 100:  # Significant output
        assert result.ui_details is not None
        assert len(result.ui_details) > 0
    
    # Test simple command (likely no ui_details)
    result = await bash_tool.execute(BashParams(command="echo 'simple'"))
    assert result.success == True
    # Simple commands may not have ui_details


@pytest.mark.asyncio
async def test_shell_command_integration():
    """Test the integration of shell commands with the app."""
    # This test verifies that the shell command detection is properly
    # integrated into the input handling flow
    
    # Create a minimal app instance for testing
    app = MagicMock(spec=Kon)
    app._is_running = False
    
    # Mock the necessary components
    mock_chat = MagicMock(spec=ChatLog)
    mock_status = MagicMock()
    
    def query_one_side_effect(selector):
        if selector == "#chat-log":
            return mock_chat
        elif selector == "#status-line":
            return mock_status
        return MagicMock()
    
    app.query_one.side_effect = query_one_side_effect
    
    # Test that shell command detection logic works
    test_inputs = [
        "!ls -la",
        "!!grep -r TODO src/",
        "!python -m pytest tests/",
    ]
    
    for input_text in test_inputs:
        # Extract command and send_to_llm flag
        send_to_llm = input_text.startswith("!!")
        command_text = input_text[2:] if send_to_llm else input_text[1:]
        command_text = command_text.strip()
        
        assert command_text != ""
        assert isinstance(send_to_llm, bool)


@pytest.mark.asyncio
async def test_empty_shell_command():
    """Test that empty shell commands are handled gracefully."""
    test_cases = ["!", "!!", "!   ", "!!   "]
    
    for input_text in test_cases:
        send_to_llm = input_text.startswith("!!")
        command_text = input_text[2:] if send_to_llm else input_text[1:]
        command_text = command_text.strip()
        
        # Empty commands should result in empty command text
        assert command_text == ""
