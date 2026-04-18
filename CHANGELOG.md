# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- No changes yet.

## 0.3.5 - 2026-04-18

### Added

- Standalone session HTML export with self-contained styling.
- Configurable request timeout for API calls - @jspruit.
- GitHub CI tests for Python 3.12–3.13 - @sukhbinder.
- Width-aware popup lists and queue display.

### Changed

- Highlight color applied to the second column in floating lists.
- Batch scroll during streaming, cache query_one lookups, pause spinner timer when idle.
- Diff line length capped at 200 characters.

### Fixed

- Persist thinking level in session header and change all defaults to high.
- Normalize OpenAI provider imports.
- Widen resume popup labels.
- Remove unused UI app import.

### Performance

- Added `gc.freeze()` and `PAUSE_GC_ON_SCROLL` to reduce GC stutters.

## 0.3.4 - 2026-04-10

### Fixed

- Fixed Windows UTF-8 encoding errors in file operations - @sukhbinder.
- Fixed local Gemma model thinking block compatibility.
- Removed duplicate force-include for builtin skills in build config.

### Changed

- Updated local model documentation.

## 0.3.3 - 2026-04-08

### Added

- Added queued agent steering between turns - @0xku.
- Added bundled `/init` slash command for project scaffolding - @0xku.
- Added help info for queue and steer queue commands.
- Added GLM-5.1 support for zai provider.

### Changed

- Improved read tool directory listings.
- Updated README with steer queue documentation.
- Added `$` icon for bash, `%` for web tools, and `←` for edit tool.
- Used muted color for shortcut key hints in exit/delete prompts.

### Fixed

- Let ESC interrupt retry backoff immediately - @0xku.
- Fixed OpenAI login stdin leak by removing orphaned thread - @Meltedd.
- Fixed OpenAI and Anthropic local compat with auth flags.
- Fixed interrupt handling before handoff thread switch.
- Fixed subprocess communication drain on cancellation/timeout.
- Added zipfile path traversal validation.
- Removed token throughput metrics.

## 0.3.2 - 2026-03-22

### Added

- Added a `collapse_thinking` config flag to control thinking block display.
- Added a Ghostty theme preview script.

### Changed

- Improved theme and model picker indicators.
- Refactored tool display helpers into shared `truncate_text` and `shorten_path` utilities.

### Fixed

- Fixed duplicate skill warnings coming from the home directory.

## 0.3.1 - 2026-03-21

### Added

- Added optional built-in web tools (`web_search`, `web_fetch`) configurable via `--extra-tools` and config - @Meltedd.
- Added tool permission controls with bash safety analysis - @Meltedd.
- Added popular built-in themes.
- Added tool previews in approval prompts.

### Changed

- Updated the default config shape to use `ui.theme`, add `tools` and `permissions` sections, and simplify agent loop defaults.
- Refreshed README/config/local-model docs and clarified custom skill slash commands.
- Improved plain-text tool call displays, approval UI presentation, and thinking/input styling.

### Fixed

- Fixed session loading to rebuild the agent and persist the session system prompt.
- Fixed session file handling by tightening session directory permissions and tarfile path filtering.
- Fixed update-version check behavior and shortened web fetch extraction errors.
- Fixed collapsed thinking block rendering, exit summary theming, and summary formatting polish.
- Fixed skill collision warning path formatting to display consistently.

## 0.3.0 - 2026-03-15

### Added

- Added `/handoff` to start a focused handoff in a new session, including handoff links between sessions.
- Added Azure AI Foundry provider support for Anthropic models.
- Added configurable Git context controls in the system prompt.
- Added startup launch warnings for provider/config/skill initialization issues.
- Added dotted spinner statuses for handoff and auto-compaction.
- Added resume-list improvements for skill-trigger sessions and session deletion.
- Added file change tracking from edit/write tools, including InfoBar counters and details modal.
- Added incremental markdown rendering during streaming with heading color support.
- Added adaptive thinking support for Claude 4.6 models.
- Added richer exit summary with KON logo, elapsed duration, and file-change totals.

### Changed

- Improved model picker ordering by provider and model id.
- Improved status line token display to show raw streaming token counts.
- Improved handoff marker/link rendering for cleaner output.
- Updated README intro/config guidance and model/provider documentation.

### Fixed

- Fixed Anthropic stream handling by dropping unsigned thinking blocks, leading empty text chunks, and empty assistant messages.
- Fixed tool error propagation so failures are sent back to the model in tool result content.
- Fixed file change stats reset behavior on `/new` and `/clear`.
- Fixed markdown finalization to preserve block-level structure after streaming.
- Fixed editor/input UX regressions (newline border flicker and truncation/history cycling conflicts).
- Fixed git-status prompt spacing and reduced git-context prompt cap for stability.

## 0.2.7 - 2026-03-14

### Added

- Added automatic user config migration with schema versioning and backup creation (`~/.kon/config.toml.bak.<timestamp>`).
- Added migration tests for legacy config key upgrades and no-op behavior on current schema versions.
- Added provider error-format tests to ensure empty upstream exceptions render with readable fallback text.

### Fixed

- Fixed blank error notifications (`✗` with no message) by normalizing empty provider/UI error messages.

## 0.2.6 - 2026-03-14

### New Features

- Added slash-triggered skill workflow in the TUI.

### Added

- Added clearer UI highlighting for informational/system notices.
- Added regression tests for compaction behavior and update notice behavior.
- Added a direct changelog link in update-available notices.

### Changed

- Improved tool output presentation, including truncated output labels and bash previews.
- Refined loaded resource headers in chat (`[Context]` and `[Skills]`) for better scanning.
- Renamed warning color usage to `notice` in UI color configuration for consistency.
- Simplified update notifications to always show the repository changelog URL.
- Updated README skills docs with `register_cmd` and `cmd_info` front matter fields and validation rules.

### Fixed

- Fixed compaction usage accounting by backtracking token usage correctly.
- Fixed markdown heading rendering by sanitizing inline code ticks.
- Fixed skill-trigger prompt formatting edge cases in UI messages.
- Removed italic styling from thinking blocks in both TUI and exported transcripts.

## 0.2.5 - 2026-03-14

- Added update-available notice in TUI.
- Improved configuration and context loading behavior.
- Added tests for update notice behavior.
