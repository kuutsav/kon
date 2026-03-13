"""
AGENTS.md discovery and loading.

Discovers AGENTS.md (or CLAUDE.md) files from:
1. Global config dir (~/.kon/)
2. Ancestor directories from cwd up to git root or home directory (closest last)
"""

from dataclasses import dataclass
from pathlib import Path

from .. import escape_xml, get_config_dir

CONTEXT_FILE_CANDIDATES = ["AGENTS.md", "CLAUDE.md"]


@dataclass
class ContextFile:
    path: str
    content: str


def _find_git_root(start: Path) -> Path | None:
    current = start
    while True:
        if (current / ".git").is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _get_stop_directory(cwd: Path) -> Path:
    git_root = _find_git_root(cwd)
    if git_root:
        return git_root

    home = Path.home()
    try:
        cwd.relative_to(home)
        return home
    except ValueError:
        return cwd


def _load_context_from_dir(directory: Path) -> ContextFile | None:
    for filename in CONTEXT_FILE_CANDIDATES:
        filepath = directory / filename
        if filepath.is_file():
            try:
                content = filepath.read_text(encoding="utf-8")
                return ContextFile(path=str(filepath), content=content)
            except Exception:
                pass
    return None


def load_agents_files(cwd: str | None = None) -> list[ContextFile]:
    """
    Load all AGENTS.md files from config dir and ancestor directories.

    Discovery order:
    1. Global config dir (~/.kon/) - loaded first
    2. Ancestor directories from stop dir down to cwd - closest to cwd loaded last

    Stop directory is determined by:
    - Git root (if cwd is inside a git repository)
    - Home directory (otherwise)

    This means project-specific instructions appear after global ones.
    """
    resolved_cwd = Path(cwd) if cwd else Path.cwd()
    resolved_cwd = resolved_cwd.resolve()

    context_files: list[ContextFile] = []
    seen_paths: set[str] = set()

    # 1. Load from global config dir
    config_dir = get_config_dir()
    if config_dir.exists():
        global_context = _load_context_from_dir(config_dir)
        if global_context:
            context_files.append(global_context)
            seen_paths.add(global_context.path)

    # 2. Determine stop directory (git root or home)
    stop_dir = _get_stop_directory(resolved_cwd)

    # 3. Collect from ancestors (stop_dir to cwd, so closest is last)
    ancestor_files: list[ContextFile] = []
    current = resolved_cwd

    while True:
        context_file = _load_context_from_dir(current)
        if context_file and context_file.path not in seen_paths:
            ancestor_files.insert(0, context_file)
            seen_paths.add(context_file.path)
        if current == stop_dir:
            break
        current = current.parent

    context_files.extend(ancestor_files)

    return context_files


def format_agents_files_for_prompt(agents_files: list[ContextFile]) -> str:
    if not agents_files:
        return ""

    lines = [
        "# Project Context",
        "",
        "Project guidelines for coding agents.",
        "",
        "<project_guidelines>",
    ]

    for ctx in agents_files:
        lines.append(f'<file path="{escape_xml(ctx.path)}">')
        lines.append(escape_xml(ctx.content))
        lines.append("</file>")

    lines.append("</project_guidelines>")

    return "\n".join(lines)
