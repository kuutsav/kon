# Architecture Review: Separation of Concerns

## Overall assessment

The architecture has strong core foundations, but the boundary between the runtime and the TUI is flatter than it should be.

At the inner runtime level, the split is good:

- **`session.py`** owns append-only persistence and session-derived state.
- **`turn.py`** owns a single streaming LLM/tool execution cycle.
- **`loop.py`** owns the multi-turn agent loop, persistence of turn outputs, and overflow compaction.
- **`events.py`** provides the event boundary that the UI consumes.

That part is well-designed.

The main issue is not that the UI is running the agent loop itself. The main issue is that **the UI is also acting as the controller/runtime coordinator**, especially around session restoration, provider reconfiguration, model switching, handoff, and manual compaction.

## What is clean today

### Core runtime

#### `session.py`

Mostly a clean persistence layer:

- append-only JSONL storage
- load/list/continue operations
- session entry types
- compacted vs full message views
- persisted model and thinking-level history

This is a good responsibility boundary.

#### `turn.py`

A strong single-turn runtime boundary:

- streams provider output
- tracks active stream state
- collects tool calls
- permission-checks and waits for approval
- executes tools
- emits typed stream events

This file is clearly part of the core runtime, not the UI.

#### `loop.py`

`Agent.run()` is a proper multi-turn orchestrator:

- appends the user message
- runs turns
- persists assistant and tool-result messages
- handles interruption and stop conditions
- performs automatic compaction
- emits higher-level lifecycle events

This is the right place for multi-turn agent behavior.

#### `events.py`

The event model is the right abstraction. During execution, the TUI mostly behaves as an event consumer and renderer.

## Where the UI is overstepping

The UI is not doing the actual agentic turn logic, but it **is doing too much runtime/session-management work**.

### 1. Provider lifecycle management is duplicated in UI

Provider creation and reconfiguration are spread across multiple places:

- `ui/app.py::on_mount`
- `ui/session_ui.py::_load_session`
- `ui/commands.py::_select_model`
- `ui/commands.py::_create_new_session`

These code paths all repeat variants of the same logic:

- determine provider/api type
- build `ProviderConfig`
- recreate provider if needed
- otherwise mutate existing provider config

This is application/runtime logic, not view logic.

### 2. Agent construction and reconfiguration are duplicated

The same agent wiring appears multiple times:

- build or restore the system prompt
- construct an `Agent`
- or mutate the current agent to point at a new session/provider/tools

This currently happens in:

- `ui/app.py::on_mount`
- `ui/session_ui.py::_load_session`
- `ui/app.py::_run_agent`
- `ui/commands.py::_reset_session_ui` indirectly via mutation/reload

That duplication is a sign that the UI is compensating for a missing orchestration layer.

### 3. The UI pushes runtime state into `Agent`

Before each run, the UI mutates the agent from the outside:

- `self._agent.provider = self._provider`
- `self._agent.session = self._session`
- `self._agent.tools = self._tools`
- `self._agent.config.context_window = ...`
- `self._agent.config.max_output_tokens = ...`

This makes `Agent` feel only partially in charge of its own state. It also creates sync risks: if one UI path forgets to update one field, the runtime can become inconsistent. The session resume test added for the persisted system prompt bug is a concrete example of this failure mode.

### 4. Manual compaction duplicates core compaction behavior

`ui/commands.py::_do_compact` reimplements logic that is conceptually owned by the runtime:

- inspect latest usage
- generate a summary
- append a compaction entry

The command is valid, but the implementation should be delegated to a non-UI service or controller instead of living directly in the command handler.

### 5. Handoff workflow is owned by the UI

`ui/commands.py::_do_handoff` is not just presentation logic. It performs a full workflow:

- generate a focused handoff prompt
- create a new session
- write backlink/forward-link metadata
- persist both sessions
- swap active runtime state

This is real application behavior. The UI should trigger it, not implement it.

### 6. Session stats and queries are in UI helpers

These are pure data queries over session entries:

- `SessionUIMixin._calculate_session_tokens`
- `SessionUIMixin._calculate_session_file_changes`
- much of `/session` counting logic in `ui/commands.py::_show_session_info`

These belong on `Session` or in a dedicated session-stats/query helper, not in the UI layer.

## What is properly in the UI

These responsibilities are fine in the TUI:

- consuming agent events and rendering them
- `ChatLog` widget behavior and block management
- keybindings and approval input (`y` / `n`)
- completion UI and selection lists
- replaying stored session entries into widgets
- status line, queue display, theme selection, clipboard/export triggers

So the UI is not incorrectly taking over the core turn loop. The problem is that it also owns too much runtime setup and coordination outside the loop.

## Additional architectural leaks worth noting

The core/runtime boundary is good, but not perfectly pure. A few pragmatic leaks already exist.

### 1. Core message types include UI-facing fields

`ToolResult` and `ToolResultMessage` in `core/types.py` include:

- `ui_summary`
- `ui_details`

This is practical and convenient, but it means presentation data is embedded in the canonical runtime message model.

### 2. `turn.py` computes display-ready tool strings

`turn.py` calls tool formatting methods like:

- `tool.format_call(...)`
- `tool.format_preview(...)`

That means the core runtime is not completely presentation-agnostic.

### 3. The event boundary carries an approval future

`ToolApprovalEvent` includes an `asyncio.Future`, which makes the event protocol interactive rather than purely declarative. Again, pragmatic, but not a perfectly clean boundary.

### 4. `session.py` knows about skill-trigger message encoding

`Session._extract_preview_from_user_message()` understands the `[skill]` / `[query]` structure used by the app. That is application-level knowledge inside the session layer.

These leaks are not severe, but they are worth recognizing if the goal is stricter layering over time.

## Root cause

The root issue is a missing layer between:

- the pure runtime (`session.py`, `turn.py`, `loop.py`)
- and the TUI (`ui/*`)

`Agent` is close to being that middle layer, but today it is primarily a **run-time executor**. It knows how to run a conversation. It does **not** fully own the surrounding lifecycle concerns:

- provider creation/recreation
- loading or swapping sessions
- model switching
- manual compaction
- handoff workflow
- session-derived stats

Because that layer is missing, the TUI has absorbed the work.

## Recommendation: add a thin controller/runtime manager

The highest-value improvement is to introduce a thin non-UI orchestration layer. This could be called something like:

- `ConversationController`
- `RuntimeManager`
- `SessionRuntime`

Its responsibilities should include:

1. provider construction and reconfiguration
2. session creation/load/resume
3. stable `Agent` creation and ownership
4. model switching
5. thinking-level updates
6. manual compaction
7. handoff workflow
8. session stats and derived queries

Then the UI becomes much simpler:

- ask controller to do something
- render returned state/events/results
- stop mutating the runtime graph directly

## Important design note: do not just turn `Agent` into a god object

Some of the duplicated logic could move onto `Agent`, but there is a risk in stuffing everything into it.

Today `Agent` is nicely focused on execution. If session loading, provider creation, model switching, handoff, compaction, export context, and stats all get added onto `Agent`, it may become a giant all-purpose object.

A separate controller/service layer is likely the cleaner long-term move:

- keep `Agent` focused on running turns
- keep `Session` focused on persistence and session queries
- let the controller own lifecycle/orchestration
- let the UI focus on rendering and user input

## Recommended refactor targets

### Short-term

1. **Move session stats onto `Session`**
   - cumulative token totals
   - latest context tokens
   - file change aggregation
   - message/tool counts for `/session`

2. **Extract provider/session/agent wiring into one place**
   - one code path for startup, resume, load-session, and model switch

3. **Move manual compaction behind a non-UI method**
   - e.g. `controller.compact_now()` or equivalent

4. **Move handoff workflow behind a non-UI method**
   - UI should only trigger it and then rerender the result

### Medium-term

5. **Stop mutating `Agent` from multiple UI paths**
   - the controller should own the active agent/runtime instance
   - replace scattered field assignment with a single reconfigure/swap operation

6. **Reduce duplicated system-prompt restoration logic**
   - centralize `session.system_prompt or build_system_prompt(...)`

### Long-term / optional cleanup

7. **Decide how pure you want the runtime boundary to be**
   - keep `ui_summary/ui_details` in core for pragmatism, or move them behind a presentation adapter
   - consider whether tool display formatting should stay in runtime or move outward
   - consider replacing the approval future in events with a stricter request/response boundary if desired

## Final verdict

### Current state

- **Core runtime architecture:** strong
- **UI as renderer during execution:** mostly good
- **Overall separation of concerns:** decent but flattened
- **Main architectural gap:** missing controller/application layer

### Honest conclusion

The UI is **not** doing the core turn engine or multi-turn reasoning loop. That part is correctly placed in the core.

However, the UI **is** overstepping in an important way: it currently owns too much session-management and runtime-lifecycle logic. That includes creating and reconfiguring providers, swapping sessions, rebuilding agents, handling handoff, and performing manual compaction.

So the answer is:

> The architecture has good bones, but the TUI is carrying too much runtime orchestration. The next architectural improvement should be extracting a thin controller/service layer between core and UI.

## Suggested score

- **Core architecture:** 8/10
- **Overall separation including UI:** 6/10
- **Refactor urgency:** worth doing before more commands/features accumulate
