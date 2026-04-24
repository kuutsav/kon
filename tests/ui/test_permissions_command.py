"""Test the /permissions slash command functionality."""

from kon.ui.autocomplete import DEFAULT_COMMANDS, SlashCommand
from kon.ui.selection_mode import SelectionMode
from kon.ui.commands import CommandsMixin


def test_permissions_command_in_default_commands():
    """Test that the permissions command is in the default commands list."""
    permissions_cmd = None
    for cmd in DEFAULT_COMMANDS:
        if cmd.name == "permissions":
            permissions_cmd = cmd
            break
    
    assert permissions_cmd is not None, "Permissions command not found in DEFAULT_COMMANDS"
    assert permissions_cmd.description == "Change permission mode"
    assert isinstance(permissions_cmd, SlashCommand)


def test_permissions_selection_mode():
    """Test that PERMISSIONS selection mode exists."""
    assert hasattr(SelectionMode, "PERMISSIONS")
    assert SelectionMode.PERMISSIONS == "permissions"


def test_permissions_command_handler_exists():
    """Test that the permission command handler methods exist."""
    assert hasattr(CommandsMixin, "_handle_permissions_command")
    assert hasattr(CommandsMixin, "_select_permission_mode")


def test_permissions_command_in_help():
    """Test that permissions command is mentioned in help text."""
    # Check that the help text includes the permissions command
    import inspect
    source = inspect.getsource(CommandsMixin._show_help)
    assert "/permissions" in source
    assert "Change permission mode" in source