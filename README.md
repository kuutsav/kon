# Dot

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Dot is a minimal coding agent that just works.

It has a tiny harness: about **215 tokens** for the system prompt and around **600 tokens** for tool definitions – so **under 1k tokens** before conversation context.

At the time of writing this README (**22 Feb 2026**), this repo has **108 files** and is easy to understand in a weekend. Here’s a rough file-count comparison against a couple of popular OSS coding agents:

Others are of course more mature, support more models, include broader test coverage, and cover more surfaces. But if you want a truly minimal coding agent with batteries included – something you can understand, fork, and extend quickly – Dot might be interesting.

```bash
$ fd . | cut -d/ -f1 | sort | uniq -c | sort -rn
4107 opencode
 740 pi-mono
 108 dot
```

## Setup

### Warning

> [!WARNING]
> Platform support: macOS and Linux are supported; Windows is not tested yet.

### Prerequisites

Python 3.12+ and [uv](https://github.com/astral-sh/uv).

### Install (recommended)

```bash
uv tool install dot-coding-agent
```

This installs `dot` globally as a CLI tool.

### Install from source (advanced)

```bash
git clone <repository-url>
cd dot
uv tool install .
```

### Run

```bash
dot
```

CLI options:

```text
usage: dot [-h] [--model MODEL]
           [--provider {github-copilot,openai,openai-codex,openai-responses,zhipu}]
           [--api-key API_KEY] [--base-url BASE_URL] [--continue]
           [--resume RESUME_SESSION]

Dot TUI

options:
  -h, --help            show this help message and exit
  --model, -m MODEL     Model to use
  --provider, -p {github-copilot,openai,openai-codex,openai-responses,zhipu}
                        Provider to use
  --api-key, -k API_KEY
                        API key
  --base-url, -u BASE_URL
                        Base URL for API
  --continue, -c        Resume the most recent session
  --resume, -r RESUME_SESSION
                        Resume a specific session by ID (full or unique
                        prefix)
```

### Tool binaries

- **[fd](https://github.com/sharkdp/fd)** – required for fast file discovery; Dot auto-downloads it only if it's missing.
- **[ripgrep (rg)](https://github.com/BurntSushi/ripgrep)** – required for fast content search; Dot auto-downloads it only if it's missing.
- **[eza](https://github.com/eza-community/eza)** (optional) – supports `.gitignore`-aware listings and usually emits fewer tokens than `ls`.

## OAuth and API keys

- **GitHub Copilot OAuth**: run `/login` and choose GitHub Copilot.
- **OpenAI OAuth (Codex)**: run `/login` and choose OpenAI. Dot supports callback flow plus manual paste fallback.
- **OpenAI-compatible providers (for example ZhiPu)**: set an API key via environment variable (`OPENAI_API_KEY` or `ZAI_API_KEY`).

## Features

### Tools

| Tool   | Purpose |
| ------ | ------- |
| `read` | Read file contents (pagination for large files, image support) |
| `edit` | Surgical find-and-replace edits |
| `write` | Create or overwrite files |
| `bash` | Execute shell commands |
| `grep` | Search file contents with regex |
| `find` | Find files by glob pattern |

### Slash commands

Type `/` at the start of input to see available commands.

| Command | Description |
| ------- | ----------- |
| `/new` | Start a new conversation and reload project context/skills |
| `/resume` | Browse and restore a saved session |
| `/model` | Switch model via interactive picker |
| `/session` | Show session metadata and token stats |
| `/compact` | Compact the current conversation immediately |
| `/export` | Export current session to HTML |
| `/copy` | Copy last assistant response to clipboard |
| `/login` | Authenticate with a provider |
| `/logout` | Log out from a provider |
| `/clear` | Clear current conversation |
| `/help` | Show commands and keybindings |
| `/quit` (`/exit`, `/q`) | Quit Dot |

### `@` file and folder search

Type `@` + query to fuzzy-search files/folders in the current project and insert paths into your prompt.

### Tab path autocomplete

Press **Tab** in the input box to complete paths (`~`, `./`, `../`, absolute paths, quoted paths, etc.).

### Query queueing

If the agent is currently running, you can still submit more prompts. Dot queues them and runs them in order once the current task finishes (up to 5 queued prompts).

### Sessions

Sessions are append-only JSONL files under `~/.dot/sessions/`.

- `/resume` to reopen past sessions
- `/session` for message/token stats
- `/export` for standalone HTML transcripts
- `--continue` / `-c` to continue the most recent session from CLI

### AGENTS.md

Dot loads project guidelines from `AGENTS.md` (or `CLAUDE.md`) files into the system prompt:

1. Global: `~/.dot/AGENTS.md`
2. Ancestor directories from git root (or home) down to current working directory

### Skills

Skills are reusable instruction packs loaded from:

- Project: `.dot/skills/`
- Global: `~/.dot/skills/`

Each skill has a `SKILL.md` file with front matter:

```markdown
---
name: my-skill
description: Brief description of what this skill does
---

# My Skill

Detailed instructions for the agent...
```

For skills with scripts, see [Agent Skills Documentation](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

## Architecture

```text
LLM Provider
    │
    │ StreamPart (TextPart, ThinkPart, ToolCallStart, ToolCallDelta, ...)
    ▼
Single Turn (turn.py)
    │
    │ StreamEvent (ThinkingStart/Delta/End, TextStart/Delta/End, ToolStart/End, ToolResult, ...)
    ▼
Agentic Loop (loop.py)
    │
    │ Event (AgentStart, TurnStart, TurnEnd, AgentEnd + all StreamEvents)
    ▼
UI (app.py)
```

## Supported Models

| Model | Provider | Thinking | Vision |
| ----- | -------- | -------- | ------ |
| `glm-4.7` | ZhiPu | Yes | No |
| `glm-5` | ZhiPu | Yes | No |
| `claude-sonnet-4.5` | GitHub Copilot | Yes | Yes |
| `claude-opus-4.5` | GitHub Copilot | Yes | Yes |
| `claude-sonnet-4.6` | GitHub Copilot | Yes | Yes |
| `claude-opus-4.6` | GitHub Copilot | Yes | Yes |
| `gpt-5.3-codex` | GitHub Copilot | Yes | Yes |
| `gpt-5.3-codex` | OpenAI Codex | Yes | Yes |

## Configuration

Config lives at `~/.dot/config.toml` (auto-created on first run).

Most important knobs:

- `llm.default_provider`
- `llm.default_model`
- `llm.default_thinking_level`
- `llm.system_prompt` (**you can fully override Dot’s system prompt here**)
- `compaction.on_overflow`, `compaction.buffer_tokens`, `compaction.default_context_window`

You can also theme the UI via `[ui.colors]` values.

Example:

```toml
[llm]
default_provider = "openai-codex"
default_model = "gpt-5.3-codex"
default_thinking_level = "high"
system_prompt = """Your custom system prompt here"""

[compaction]
on_overflow = "continue"
buffer_tokens = 20000
```

## Development setup

For hacking on Dot locally:

```bash
uv sync
uv run dot
uv run ruff format .
uv run pytest
```

## Acknowledgements

- Dot takes significant inspiration from [`pi-mono` coding-agent](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent), especially in terms of the overall philosophy and UI design.
  - Why not just use pi? Pi is no longer a small project, and I want to be in complete control of my coding agent.
  - I mostly agree with Mario (author of pi), but I have different beliefs on some matters - for example, subagents (especially useful for context gathering in larger repos when paired with semantic search tools).
  - Over time, I also want to give more preference to local LLMs I can run. `glm-4.7-flash` and `qwen-3-coder-next` look promising, so I may make decisions that do not necessarily optimize for SOTA paid models.
- Dot also borrows ideas from [Amp](https://ampcode.com/), Claude Code, and other coding agents.

## LICENCE

MIT
