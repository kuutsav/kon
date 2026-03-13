from pathlib import Path

from kon.context.agents import (
    ContextFile,
    _find_git_root,
    _get_stop_directory,
    _load_context_from_dir,
    escape_xml,
    format_agents_files_for_prompt,
    load_agents_files,
)


class TestFindGitRoot:
    def test_finds_git_root(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        subdir = tmp_path / "src" / "deep"
        subdir.mkdir(parents=True)

        result = _find_git_root(subdir)

        assert result == tmp_path

    def test_no_git_root(self, tmp_path):
        subdir = tmp_path / "no" / "git" / "here"
        subdir.mkdir(parents=True)

        result = _find_git_root(subdir)

        assert result is None

    def test_git_root_is_start_dir(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = _find_git_root(tmp_path)

        assert result == tmp_path

    def test_nested_git_repos(self, tmp_path):
        outer_git = tmp_path / ".git"
        outer_git.mkdir()

        inner = tmp_path / "inner"
        inner_git = inner / ".git"
        inner.mkdir()
        inner_git.mkdir()

        deep = inner / "deep"
        deep.mkdir()

        result = _find_git_root(deep)

        assert result == inner


class TestGetStopDirectory:
    def test_returns_git_root_when_present(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        subdir = tmp_path / "src"
        subdir.mkdir()

        result = _get_stop_directory(subdir)

        assert result == tmp_path

    def test_returns_home_when_under_home(self, tmp_path, monkeypatch):
        home = tmp_path / "home" / "user"
        home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: home)

        project = home / "projects" / "myapp"
        project.mkdir(parents=True)

        result = _get_stop_directory(project)

        assert result == home

    def test_returns_cwd_when_not_under_home(self, tmp_path, monkeypatch):
        home = tmp_path / "home" / "user"
        home.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: home)

        outside = tmp_path / "mnt" / "external"
        outside.mkdir(parents=True)

        result = _get_stop_directory(outside)

        assert result == outside


class TestLoadContextFileFromDir:
    def test_loads_agents_md(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Project Guidelines")

        result = _load_context_from_dir(tmp_path)

        assert result is not None
        assert result.content == "# Project Guidelines"
        assert "AGENTS.md" in result.path

    def test_loads_claude_md_fallback(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("# Claude Guidelines")

        result = _load_context_from_dir(tmp_path)

        assert result is not None
        assert result.content == "# Claude Guidelines"
        assert "CLAUDE.md" in result.path

    def test_prefers_agents_over_claude(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# AGENTS content")
        (tmp_path / "CLAUDE.md").write_text("# CLAUDE content")

        result = _load_context_from_dir(tmp_path)

        assert result is not None
        assert "AGENTS content" in result.content

    def test_no_context_file(self, tmp_path):
        result = _load_context_from_dir(tmp_path)

        assert result is None

    def test_ignores_directories_with_same_name(self, tmp_path):
        agents_dir = tmp_path / "AGENTS.md"
        agents_dir.mkdir()

        result = _load_context_from_dir(tmp_path)

        assert result is None


class TestLoadAgentsFiles:
    def test_loads_from_cwd(self, tmp_path, monkeypatch):
        monkeypatch.setattr("kon.context.agents.get_config_dir", lambda: tmp_path / "config")

        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()
        (project / "AGENTS.md").write_text("# Project rules")

        result = load_agents_files(str(project))

        assert len(result) == 1
        assert "Project rules" in result[0].content

    def test_loads_from_ancestors(self, tmp_path, monkeypatch):
        monkeypatch.setattr("kon.context.agents.get_config_dir", lambda: tmp_path / "config")

        root = tmp_path / "repo"
        (root / ".git").mkdir(parents=True)
        (root / "AGENTS.md").write_text("# Root rules")

        subdir = root / "src" / "deep"
        subdir.mkdir(parents=True)
        (subdir / "AGENTS.md").write_text("# Deep rules")

        result = load_agents_files(str(subdir))

        assert len(result) == 2
        assert "Root rules" in result[0].content
        assert "Deep rules" in result[1].content

    def test_global_config_loaded_first(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "AGENTS.md").write_text("# Global rules")
        monkeypatch.setattr("kon.context.agents.get_config_dir", lambda: config_dir)

        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()
        (project / "AGENTS.md").write_text("# Project rules")

        result = load_agents_files(str(project))

        assert len(result) == 2
        assert "Global rules" in result[0].content
        assert "Project rules" in result[1].content

    def test_no_duplicates(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.setattr("kon.context.agents.get_config_dir", lambda: config_dir)

        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()
        (project / "AGENTS.md").write_text("# Single file")

        result = load_agents_files(str(project))

        paths = [r.path for r in result]
        assert len(paths) == len(set(paths))

    def test_ordering_closest_last(self, tmp_path, monkeypatch):
        monkeypatch.setattr("kon.context.agents.get_config_dir", lambda: tmp_path / "config")

        root = tmp_path / "repo"
        (root / ".git").mkdir(parents=True)
        (root / "AGENTS.md").write_text("# 1-root")

        mid = root / "packages"
        mid.mkdir()
        (mid / "AGENTS.md").write_text("# 2-mid")

        leaf = mid / "app"
        leaf.mkdir()
        (leaf / "AGENTS.md").write_text("# 3-leaf")

        result = load_agents_files(str(leaf))

        assert len(result) == 3
        assert "1-root" in result[0].content
        assert "2-mid" in result[1].content
        assert "3-leaf" in result[2].content

    def test_empty_when_no_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr("kon.context.agents.get_config_dir", lambda: tmp_path / "config")

        project = tmp_path / "empty"
        project.mkdir()
        (project / ".git").mkdir()

        result = load_agents_files(str(project))

        assert result == []


class TestEscapeXml:
    def test_escapes_ampersand(self):
        assert escape_xml("AT&T") == "AT&amp;T"

    def test_escapes_less_than(self):
        assert escape_xml("a < b") == "a &lt; b"

    def test_escapes_greater_than(self):
        assert escape_xml("a > b") == "a &gt; b"

    def test_escapes_double_quote(self):
        assert escape_xml('say "hello"') == "say &quot;hello&quot;"

    def test_escapes_single_quote(self):
        assert escape_xml("say 'hello'") == "say &apos;hello&apos;"

    def test_escapes_multiple_special_chars(self):
        assert (
            escape_xml('<script>alert("AT&T")</script>')
            == "&lt;script&gt;alert(&quot;AT&amp;T&quot;)&lt;/script&gt;"
        )

    def test_preserves_normal_text(self):
        assert escape_xml("Hello World 123") == "Hello World 123"


class TestFormatAgentsFilesForPrompt:
    def test_empty_list(self):
        result = format_agents_files_for_prompt([])
        assert result == ""

    def test_single_file(self):
        files = [ContextFile(path="/path/to/AGENTS.md", content="Use pytest for tests.")]

        result = format_agents_files_for_prompt(files)

        assert "# Project Context" in result
        assert "Project guidelines for coding agents." in result
        assert '<file path="/path/to/AGENTS.md">' in result
        assert "Use pytest for tests." in result
        assert "<project_guidelines>" in result
        assert "</project_guidelines>" in result

    def test_multiple_files(self):
        files = [
            ContextFile(path="/global/AGENTS.md", content="Global rules."),
            ContextFile(path="/project/AGENTS.md", content="Project rules."),
        ]

        result = format_agents_files_for_prompt(files)

        assert '<file path="/global/AGENTS.md">' in result
        assert "Global rules." in result
        assert '<file path="/project/AGENTS.md">' in result
        assert "Project rules." in result
        # Global should come before project
        assert result.index("/global/AGENTS.md") < result.index("/project/AGENTS.md")
