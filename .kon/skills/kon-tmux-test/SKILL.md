---
name: kon-tmux-test
description: E2E testing of kon using tmux sessions; IMPORTANT: only trigger this skill when user asks for e2e testing of kon
---

# Kon Tmux E2E Testing

End-to-end testing of kon using tmux sessions to programmatically control the TUI application.

## Why Tmux?

Kon is a TUI (Textual-based) app. Running tests programmatically is hard. Tmux provides:

- `tmux new-session` - isolate test environment
- `tmux send-keys` - send keyboard input
- `tmux capture-pane` - capture output
- `tmux has-session` - check if kon is running

## Test Design Philosophy

- **Deterministic**: Shell scripts create reproducible test environments
- **Isolated config**: Tests run with `HOME=/tmp/kon-e2e-home` so runtime settings do not mutate the real user config; auth JSON files are copied into the temp HOME when present so provider startup still works
- **Separation of concerns**: Shell script runs steps and captures output; kon/the reviewer evaluates results
- **Output-based evaluation**: Test success/failure determined by reading output files, not shell script heuristics
- **UI-focused**: Test triggers (`@`, `/`, runtime pickers, keybindings) by checking UI elements appear
- **Filesystem verification**: Tool execution is verified through files under `/tmp/kon-test-project`

## Quick Start

```bash
# Run all e2e tests from the repo root
bash .kon/skills/kon-tmux-test/run-e2e-tests.sh

# Optional: keep the temporary HOME for debugging
KEEP_E2E_HOME=1 bash .kon/skills/kon-tmux-test/run-e2e-tests.sh

# Optional: override launch command/provider/model
KON_CMD='uv run kon --model gpt-5.5' \
  bash .kon/skills/kon-tmux-test/run-e2e-tests.sh
```

After running, read `/tmp/kon-test-*.txt` and evaluate the captured pane/config/filesystem outputs.

## Test Scripts

### Setup Script: `setup-test-project.sh`

Creates a deterministic test project structure at `/tmp/kon-test-project/`.

```bash
bash .kon/skills/kon-tmux-test/setup-test-project.sh
```

### Main Test Script: `run-e2e-tests.sh`

Runs comprehensive e2e tests including UI triggers, runtime controls, tab completion, and tool execution.

```bash
bash .kon/skills/kon-tmux-test/run-e2e-tests.sh
```

## Test Categories

### UI Trigger Tests (LLM-independent)

- **/ commands**: Type `/`, verify slash command list appears with core and newer commands
- **@ file search**: Type `@pyproject`, verify file picker appears with `pyproject.toml`
- **/model command**: Type `/model`, verify model selector appears, then dismiss
- **/new command**: Type `/new`, verify new conversation is started
- **/resume command**: Type `/resume`, verify session list appears, then dismiss
- **/session command**: Type `/session`, verify session info/statistics displayed

### Runtime Mode Tests (LLM-independent)

- **/permissions picker**: Shows `prompt` and `auto`, with current mode checked
- **/permissions auto/prompt**: Info bar updates (`✓✓ auto` / `⏸ prompt`) and temp config persists `permissions.mode`
- **Shift+Tab**: Cycles permission mode and persists it in temp config
- **/thinking picker**: Shows `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, with current level checked
- **/thinking minimal**: Info bar model/thinking area updates to `minimal`
- **Ctrl+Shift+T**: Cycles thinking level in the info bar
- **/notifications picker**: Shows `on` and `off`, with current mode checked
- **/notifications on/off**: Status says saved and temp config persists `notifications.enabled`
- **Info bar row2 regression**: Permission mode remains row2-left while model/provider/thinking remains row2-right after runtime changes

### Tab Path Completion Tests (LLM-independent)

- **Unique match**: Type `pypr` + Tab, verify completes to `pyproject.toml`
- **Multiple alternatives**: Type `src/kon/ui/s` + Tab, verify floating list shows `selection_mode.py`, `session_ui.py`, `styles.py`
- **Nested unique file**: Type `src/kon/ui/widg` + Tab, verify completes to `src/kon/ui/widgets.py`
- **Select from list**: Type `src/kon/ui/s` + Tab + Enter, verify first completion is applied to input

### Tool Execution Tests (Filesystem verification)

- **Write tool**: Creates `/tmp/kon-test-project/test1.txt`, verified by file existence
- **Edit tool**: Modifies `test1.txt`, verified by content changing from `hello` to `world`
- **List files**: Shows directory contents in captured pane
- **Calculation**: Computes `3+3`, verified in LLM output where practical

## Configuration

Edit or override environment variables for `run-e2e-tests.sh`:

```bash
WAIT_TIME=30                    # Time for LLM to complete all tool tasks
COMMAND_WAIT_TIME=3             # Time for UI commands to settle
SESSION_NAME="kon-test"         # Tmux session name
TEST_DIR="/tmp/kon-test-project" # Test project directory for tool execution
TEST_HOME="/tmp/kon-e2e-home"    # Isolated HOME/config/session directory
KON_DIR="$PWD"                  # Kon repo directory for tab completion tests
KON_CMD="uv run kon --model gpt-5.5"
KEEP_E2E_HOME=0                 # Set to 1 to preserve temp HOME after run
```

## Output Files

The main script writes captured outputs to `/tmp/kon-test-*.txt`:

- `/tmp/kon-test-1-commands.txt` - `/` slash command list
- `/tmp/kon-test-2-at-trigger.txt` - `@pyproject` file picker
- `/tmp/kon-test-3-model.txt` - `/model` selector
- `/tmp/kon-test-4-new.txt` - `/new` result
- `/tmp/kon-test-5-permissions-picker.txt` - `/permissions` picker
- `/tmp/kon-test-6-permissions-auto.txt` and `...-config.txt` - `/permissions auto`
- `/tmp/kon-test-7-permissions-prompt.txt` and `...-config.txt` - `/permissions prompt`
- `/tmp/kon-test-8-permissions-shift-tab.txt` and `...-config.txt` - Shift+Tab mode cycling
- `/tmp/kon-test-9-thinking-picker.txt` - `/thinking` picker
- `/tmp/kon-test-10-thinking-minimal.txt` - `/thinking minimal`
- `/tmp/kon-test-11-thinking-cycle.txt` - Ctrl+Shift+T thinking cycle
- `/tmp/kon-test-12-notifications-picker.txt` - `/notifications` picker
- `/tmp/kon-test-13-notifications-on.txt` and `...-config.txt` - `/notifications on`
- `/tmp/kon-test-14-notifications-off.txt` and `...-config.txt` - `/notifications off`
- `/tmp/kon-test-15-tab-unique.txt` - Tab completion unique match
- `/tmp/kon-test-16-tab-multiple.txt` - Tab completion alternatives
- `/tmp/kon-test-17-tab-nested-unique.txt` - Nested unique file completion
- `/tmp/kon-test-18-tab-select.txt` - Tab completion selection
- `/tmp/kon-test-19-tools.txt` - Tool execution turn
- `/tmp/kon-test-20-session.txt` - `/session` stats
- `/tmp/kon-test-21-resume.txt` - `/resume` session list
- `/tmp/kon-test-files.txt` - Test project file listing
- `/tmp/kon-test-test1-content.txt` - Final `test1.txt` content or `FILE_NOT_FOUND`
- `/tmp/kon-test-session-files.txt` - Session JSONL paths under temp HOME
- `/tmp/kon-test-final-config.txt` - Final temp config

## Key Tmux Gotchas

- **Use `Escape` not `Esc`**: tmux recognizes `Escape`. `Esc` sends literal characters.
- **Always clear input between tests**: Use `Escape` to dismiss completions, then `C-u` to clear text.
- **Completion selectors block input**: Selectors intercept Enter/Escape; dismiss them before the next test.
- **Shift+Tab**: The script sends CSI Z via `Escape '[' 'Z'` rather than relying on a tmux key name.
- **Ctrl+Shift+T**: The script sends CSI-u `Escape '[84;6u'` because `C-S-t` often collapses to Ctrl+T.

## Test Evaluation (by Kon/reviewer)

After running the test script, evaluate results by reading the output files.

### What to Check

**UI Trigger Tests:**

- `/` test: Slash command list includes `themes`, `permissions`, `thinking`, `notifications`, `init`, `compact`, `handoff`, `export`, `copy`, `login`, `logout`
- `@` test: File picker appears and shows `pyproject.toml`
- `/model` test: Model selector appears with model list/current markers
- `/new` test: `Started new conversation` appears
- `/resume` test: Session list appears with prior sessions
- `/session` test: Session info/statistics displayed

**Runtime Mode Tests:**

- `/permissions` picker shows `prompt` and `auto`, current item checked
- `/permissions auto` shows `✓✓ auto`, saved status, and config has `mode = "auto"`
- `/permissions prompt` shows `⏸ prompt`, saved status, and config has `mode = "prompt"`
- Shift+Tab toggles back to `auto` and config has `mode = "auto"`
- `/thinking` picker shows `none`, `minimal`, `low`, `medium`, `high`, `xhigh`
- `/thinking minimal` shows `Thinking level changed to minimal` and info bar row2-right includes `minimal`
- Ctrl+Shift+T changes info bar thinking level from `minimal` to the next level
- `/notifications` picker shows `on` and `off`, current item checked
- `/notifications on/off` status says saved and config flips `enabled = true/false`
- Permission mode remains in row2-left and model/provider/thinking remains row2-right

**Tab Path Completion Tests:**

- `pypr` + Tab shows `pyproject.toml`
- `src/kon/ui/s` + Tab shows `selection_mode.py`, `session_ui.py`, `styles.py`
- `src/kon/ui/widg` + Tab shows `src/kon/ui/widgets.py`
- `src/kon/ui/s` + Tab + Enter applies a selected completion

**Tool Execution Tests:**

- `/tmp/kon-test-project/test1.txt` exists
- `/tmp/kon-test-test1-content.txt` contains `world`
- `/tmp/kon-test-files.txt` lists `test1.txt`
- `/tmp/kon-test-19-tools.txt` shows relevant tool blocks/results

### Tabular Report

Provide a summary showing:

- Test name
- Status (PASS/FAIL)
- Description/failure reason
- Overall success rate

### IMPORTANT: Always offer the view command

After presenting the report, ALWAYS give the user this shell command so they can inspect raw captured outputs:

```bash
for f in /tmp/kon-test-*.txt; do printf "\n\033[1;36m▶▶▶ %s\033[0m\n" "$f"; awk 'NF{found=1} found{lines[++n]=$0} END{while(n>0 && lines[n]=="") n--; for(i=1;i<=n;i++) print lines[i]}' "$f"; done
```

## Cleanup

```bash
# Test script auto-cleans tmux session and temp HOME unless KEEP_E2E_HOME=1.
# Output files remain for evaluation (/tmp/kon-test-*.txt).
# Manual cleanup if needed:
tmux kill-session -t kon-test 2>/dev/null
rm -rf /tmp/kon-test-project /tmp/kon-e2e-home
rm -f /tmp/kon-test-*.txt
```

## Tmux Commands Reference

```bash
# Session management
tmux new-session -d -s <name> -c <dir> '<command>'
tmux kill-session -t <name>
tmux has-session -t <name>

# Input — IMPORTANT: use full key names (Escape, Enter, not Esc)
tmux send-keys -t <name> "text"
tmux send-keys -t <name> Enter
tmux send-keys -t <name> Escape
tmux send-keys -t <name> Tab
tmux send-keys -t <name> C-c
tmux send-keys -t <name> C-u

# Output
tmux capture-pane -t <name> -p
tmux capture-pane -t <name> -p > file.txt
```

## Tips

- Tests are deterministic: project/config structure is recreated each run.
- Runtime mode tests are LLM-independent and should be checked first.
- Tab completion tests run from the kon repo to use known paths.
- Tool tests verify filesystem state; avoid relying solely on LLM prose.
- Use `KEEP_E2E_HOME=1` to inspect temp config/session files after failures.
- Run tool execution before `/resume` so there is a session with messages in the list.
