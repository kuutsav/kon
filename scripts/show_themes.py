from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

KON_THEME_TO_GHOSTTY_THEME = {
    "ayu": "Ayu",
    "catppuccin-frappe": "Catppuccin Frappe",
    "catppuccin-latte": "Catppuccin Latte",
    "catppuccin-macchiato": "Catppuccin Macchiato",
    "catppuccin-mocha": "Catppuccin Mocha",
    "dracula": "Dracula",
    "everforest": "Everforest Dark Hard",
    "flexoki": "Flexoki Dark",
    "github-dark": "GitHub Dark",
    "github-light": "GitHub Light Default",
    "gruvbox-dark": "Gruvbox Dark",
    "gruvbox-light": "Gruvbox Light",
    "kanagawa": "Kanagawa Wave",
    "monokai": "Monokai Classic",
    "nightowl": "Night Owl",
    "nord": "Nord",
    "one-dark": "Atom One Dark",
    "one-light": "Atom One Light",
    "palenight": "Pale Night Hc",
    "rosepine": "Rose Pine",
    "solarized-dark": "Solarized Dark Higher Contrast",
    "solarized-light": "iTerm2 Solarized Light",
    "tokyo-day": "TokyoNight Day",
    "tokyo-night": "TokyoNight Night",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory to open before running `uv run kon -c`.",
    )
    parser.add_argument(
        "--ghostty-config",
        type=Path,
        default=Path.home() / ".config/ghostty/config",
        help="Ghostty config file to rewrite during previews.",
    )
    parser.add_argument(
        "--kon-config",
        type=Path,
        default=Path.home() / ".kon/config.toml",
        help="Kon config file to rewrite during previews.",
    )
    parser.add_argument(
        "--duration", type=float, default=10.0, help="How long each preview stays open in seconds."
    )
    parser.add_argument(
        "--pause", type=float, default=1.5, help="Pause between previews in seconds."
    )
    parser.add_argument(
        "--ghostty-app",
        type=Path,
        default=Path("/Applications/Ghostty.app"),
        help="Path to Ghostty.app for launching new macOS instances.",
    )
    return parser.parse_args()


def list_ghostty_themes() -> set[str]:
    result = subprocess.run(
        ["ghostty", "+list-themes"], check=True, capture_output=True, text=True
    )
    themes = set()
    for line in result.stdout.splitlines():
        theme = line.strip()
        if not theme:
            continue
        if theme.endswith("(resources)"):
            theme = theme[: -len("(resources)")].rstrip()
        themes.add(theme)
    return themes


def ensure_theme_mapping_is_valid(available_themes: set[str]) -> None:
    missing = {
        kon_theme: ghostty_theme
        for kon_theme, ghostty_theme in KON_THEME_TO_GHOSTTY_THEME.items()
        if ghostty_theme not in available_themes
    }
    if missing:
        lines = ["Missing Ghostty theme mappings:"]
        for kon_theme, ghostty_theme in missing.items():
            lines.append(f"  {kon_theme} -> {ghostty_theme}")
        raise RuntimeError("\n".join(lines))


def replace_or_append_theme_line(config_text: str, theme_name: str) -> str:
    lines = config_text.splitlines()
    in_ui_section = False
    ui_section_found = False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped == "[ui]":
                in_ui_section = True
                ui_section_found = True
                continue
            if in_ui_section:
                lines.insert(index, f'theme = "{theme_name}"')
                return "\n".join(lines) + "\n"
            in_ui_section = False
            continue

        if in_ui_section and stripped.startswith("theme") and "=" in stripped:
            lines[index] = f'theme = "{theme_name}"'
            return "\n".join(lines) + "\n"

    if ui_section_found:
        lines.append(f'theme = "{theme_name}"')
        return "\n".join(lines) + "\n"

    suffix = "\n" if config_text.endswith("\n") or not config_text else "\n\n"
    return f'{config_text}{suffix}[ui]\ntheme = "{theme_name}"\n'


def write_ghostty_config(config_path: Path, theme_name: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(f"theme = {theme_name}\n", encoding="utf-8")


def write_kon_theme(config_path: Path, theme_name: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    updated = replace_or_append_theme_line(original, theme_name)
    config_path.write_text(updated, encoding="utf-8")


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def launch_preview(ghostty_app: Path, project_dir: Path, duration: float) -> None:
    trap_cmd = (
        'trap \'test -n "$kon_pid" && kill -TERM "$kon_pid" 2>/dev/null || true\' EXIT INT TERM'
    )
    shell_script = (
        f"cd {sh_quote(str(project_dir))} && "
        "kon_pid='' && "
        f"{trap_cmd} && "
        "uv run kon -c & kon_pid=$! && "
        f"sleep {duration} && "
        'kill -TERM "$kon_pid" 2>/dev/null || true && '
        'wait "$kon_pid" 2>/dev/null || true'
    )
    subprocess.run(
        [
            "open",
            "-na",
            str(ghostty_app),
            "--args",
            f"--working-directory={project_dir}",
            "-e",
            "sh",
            "-lc",
            shell_script,
        ],
        check=True,
    )


def main() -> int:
    args = parse_args()
    project_dir = args.project_dir.expanduser().resolve()
    ghostty_config_path = args.ghostty_config.expanduser()
    kon_config_path = args.kon_config.expanduser()
    ghostty_app = args.ghostty_app.expanduser()

    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory does not exist: {project_dir}")
    if not ghostty_app.exists():
        raise FileNotFoundError(f"Ghostty app not found: {ghostty_app}")

    available_themes = list_ghostty_themes()
    ensure_theme_mapping_is_valid(available_themes)

    original_ghostty_config = (
        ghostty_config_path.read_text(encoding="utf-8") if ghostty_config_path.exists() else None
    )
    original_kon_config = (
        kon_config_path.read_text(encoding="utf-8") if kon_config_path.exists() else None
    )

    try:
        for kon_theme, ghostty_theme in KON_THEME_TO_GHOSTTY_THEME.items():
            print(f"Previewing kon={kon_theme} ghostty={ghostty_theme}")
            write_kon_theme(kon_config_path, kon_theme)
            write_ghostty_config(ghostty_config_path, ghostty_theme)
            launch_preview(ghostty_app, project_dir, args.duration)
            time.sleep(args.duration + args.pause + 2)
    finally:
        if original_kon_config is None:
            if kon_config_path.exists():
                kon_config_path.unlink()
        else:
            kon_config_path.write_text(original_kon_config, encoding="utf-8")

        if original_ghostty_config is None:
            if ghostty_config_path.exists():
                ghostty_config_path.unlink()
        else:
            ghostty_config_path.write_text(original_ghostty_config, encoding="utf-8")

    print("Done. Restored Ghostty and kon config files.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt as exc:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130) from exc
