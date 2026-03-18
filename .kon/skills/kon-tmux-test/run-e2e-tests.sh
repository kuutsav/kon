#!/bin/bash

# Comprehensive e2e test script for kon
# Tests UI triggers (@, / commands, Tab completion) and tool execution
# This script runs steps and captures output — evaluation is done by kon reading the output files

# Configuration
WAIT_TIME=30          # Time for LLM to complete tool tasks
COMMAND_WAIT_TIME=3   # Time for UI commands to settle
SESSION_NAME="kon-test"
TEST_DIR="/tmp/kon-test-project"
KON_DIR="$PWD"  # use caller's current working directory for tab completion tests

# Helper functions
cleanup() {
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
}

capture() {
    tmux capture-pane -t "$SESSION_NAME" -p > "$1"
}

# Dismiss any open completion/selector and clear the input line.
# Uses Escape (NOT "Esc" which tmux would send as literal text).
clear_input() {
    tmux send-keys -t "$SESSION_NAME" Escape
    sleep 0.5
    tmux send-keys -t "$SESSION_NAME" Escape
    sleep 0.5
    tmux send-keys -t "$SESSION_NAME" C-u
    sleep 0.5
}

# Cleanup on exit
trap cleanup EXIT

# === Setup ===
echo "Setting up test project..."
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR" || exit 1
echo "# Test Project" > README.md
echo '{"name": "test"}' > config.json

# Clean up old test output files
rm -f /tmp/kon-test-*.txt

# Clean up old sessions from previous runs, keep only the last 5
SESSION_DIR="$HOME/.kon/sessions/private-tmp-kon-test-project"
if [ -d "$SESSION_DIR" ]; then
    ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null
fi

# === Start kon (from kon repo for tab completion tests) ===
echo "Starting kon in tmux from kon repo..."
cleanup
tmux new-session -d -s "$SESSION_NAME" -c "$KON_DIR" 'uv run kon'
sleep 5  # Give kon time to start and render UI

# =============================================================================
# Test 1: / slash commands trigger
# Verify: typing / shows the slash command list
# =============================================================================
echo "Test 1: / slash commands trigger..."
tmux send-keys -t "$SESSION_NAME" '/'
sleep 2
capture /tmp/kon-test-1-commands.txt
clear_input

# =============================================================================
# Test 2: @ file search trigger
# Verify: typing @config shows file picker with config.json (from kon repo)
# =============================================================================
echo "Test 2: @ file search trigger..."
tmux send-keys -t "$SESSION_NAME" '@pyproject'
sleep 2
capture /tmp/kon-test-2-at-trigger.txt
clear_input

# =============================================================================
# Test 3: /model command
# Verify: /model shows model selector list, then dismiss without selecting
# =============================================================================
echo "Test 3: /model command..."
tmux send-keys -t "$SESSION_NAME" '/model'
sleep 2
# Enter applies the slash command autocomplete -> opens model selector
tmux send-keys -t "$SESSION_NAME" Enter
sleep "$COMMAND_WAIT_TIME"
capture /tmp/kon-test-3-model.txt
# Dismiss model selector without selecting (Escape hides the completion list)
clear_input

# =============================================================================
# Test 4: /new command
# Verify: /new starts a new conversation ("Started new conversation" message)
# =============================================================================
echo "Test 4: /new command..."
tmux send-keys -t "$SESSION_NAME" '/new'
sleep 2
tmux send-keys -t "$SESSION_NAME" Enter
sleep "$COMMAND_WAIT_TIME"
capture /tmp/kon-test-4-new.txt

# =============================================================================
# Test 5: Tab completion - unique match
# Verify: typing "pypr" then Tab completes to "pyproject.toml"
# =============================================================================
echo "Test 5: Tab completion - unique match..."
tmux send-keys -t "$SESSION_NAME" 'pypr'
sleep 1
tmux send-keys -t "$SESSION_NAME" Tab
sleep 2
capture /tmp/kon-test-5-tab-unique.txt
clear_input

# =============================================================================
# Test 6: Tab completion - multiple alternatives (floating list)
# Verify: typing "src/kon/ui/s" then Tab shows a list including:
# selection_mode.py, session_ui.py, styles.py
# =============================================================================
echo "Test 6: Tab completion - multiple alternatives..."
tmux send-keys -t "$SESSION_NAME" 'src/kon/ui/s'
sleep 1
tmux send-keys -t "$SESSION_NAME" Tab
sleep 2
capture /tmp/kon-test-6-tab-multiple.txt
clear_input

# =============================================================================
# Test 7: Tab completion - nested unique file
# Verify: typing "src/kon/ui/widg" then Tab completes to "src/kon/ui/widgets.py"
# =============================================================================
echo "Test 7: Tab completion - nested unique file..."
tmux send-keys -t "$SESSION_NAME" 'src/kon/ui/widg'
sleep 1
tmux send-keys -t "$SESSION_NAME" Tab
sleep 2
capture /tmp/kon-test-7-tab-home.txt
clear_input

# =============================================================================
# Test 8: Tab completion - select from list
# Verify: typing "src/kon/ui/s" Tab shows list, then Enter applies first completion
# =============================================================================
echo "Test 8: Tab completion - select from list..."
tmux send-keys -t "$SESSION_NAME" 'src/kon/ui/s'
sleep 1
tmux send-keys -t "$SESSION_NAME" Tab
sleep 2
# Select first item from floating list with Enter
tmux send-keys -t "$SESSION_NAME" Enter
sleep 1
capture /tmp/kon-test-8-tab-select.txt
clear_input

# =============================================================================
# Test 9: Tool execution (multiple tool calls)
# Verify: creates test1.txt, edits it, lists files, calculates 3+3
# Running this BEFORE /resume so there's a session with messages to resume
# Switch to test project dir first
# =============================================================================
echo "Test 9: Tool execution..."
# Change to test directory for tool execution
tmux send-keys -t "$SESSION_NAME" "/new"
sleep 1
tmux send-keys -t "$SESSION_NAME" Enter
sleep 2
tmux send-keys -t "$SESSION_NAME" "Create $TEST_DIR/test1.txt containing \"hello\", then edit $TEST_DIR/test1.txt to change \"hello\" to \"world\", list files in $TEST_DIR, and calculate 3+3. Use parallel tool calls, be quick."
sleep 1
tmux send-keys -t "$SESSION_NAME" Enter
sleep "$WAIT_TIME"
capture /tmp/kon-test-9-tools.txt

# =============================================================================
# Test 10: /session command
# Verify: shows session info (messages, tokens, file path)
# =============================================================================
echo "Test 10: /session command..."
tmux send-keys -t "$SESSION_NAME" '/session'
sleep 2
tmux send-keys -t "$SESSION_NAME" Enter
sleep "$COMMAND_WAIT_TIME"
capture /tmp/kon-test-10-session.txt

# =============================================================================
# Test 11: /resume command
# Verify: shows list of sessions (at least one from tool execution above)
# =============================================================================
echo "Test 11: /resume command..."
tmux send-keys -t "$SESSION_NAME" '/resume'
sleep 2
tmux send-keys -t "$SESSION_NAME" Enter
sleep "$COMMAND_WAIT_TIME"
capture /tmp/kon-test-11-resume.txt
# Dismiss session list without selecting
clear_input

# =============================================================================
# Capture file system state for tool execution verification
# =============================================================================
echo "Capturing file system state..."
ls -la "$TEST_DIR" > /tmp/kon-test-files.txt 2>/dev/null

# Retry a few times in case the LLM is still finishing file writes
for i in 1 2 3; do
    if [ -f "$TEST_DIR/test1.txt" ]; then
        cat "$TEST_DIR/test1.txt" > /tmp/kon-test-test1-content.txt
        break
    fi
    sleep 3
done
# Final check
if [ ! -f "$TEST_DIR/test1.txt" ]; then
    echo "FILE_NOT_FOUND" > /tmp/kon-test-test1-content.txt
    ls -la "$TEST_DIR" > /tmp/kon-test-files.txt 2>/dev/null
fi

echo ""
echo "$SEP"
echo "All tests complete"
echo "Output files saved to /tmp/kon-test-*.txt"
echo "$SEP"
