---
name: kon-release-publish
description: Tag, publish to PyPI, and create GitHub release for Kon with validation and rollback-safe steps
---

# Kon Release + PyPI Publish

Use this skill when the user asks to cut a new Kon version, tag it, publish to PyPI, and/or create a GitHub release.

## Inputs to confirm

- Target version (example: `0.2.1`)
- Base range for notes (usually previous tag, example: `v0.2.0..HEAD`)
- Whether to push `main`
- Whether to publish to PyPI now
- Whether to create GitHub release now

## Files to bump

- `pyproject.toml` → `[project].version`
- `src/kon/ui/app.py` → fallback `VERSION = "..."`
- `uv.lock` → local package version block

## Release workflow

1. **Preflight**
   - `git status --short --branch` must be clean (or confirm with user)
   - `git tag --list` and `git log --oneline <prev_tag>..HEAD` to summarize changes

2. **Version bump**
   - Update version in all 3 files above

3. **Quality gates**
   - `uv run ruff format .`
   - `uv run ruff check .`
   - `uv run pyright .`
   - `uv run pytest`

4. **Commit**
   - Commit message: `build: bump version to <version>`

5. **Tag**
   - Annotated tag: `git tag -a v<version> -m "v<version> ..."`
   - Include concise “changes since previous tag” bullets

6. **Push**
   - `git push origin main`
   - `git push origin v<version>`

7. **Build + verify artifacts**
   - `rm -rf dist && uv build`
   - `uv run python -m twine check dist/*`

8. **Publish to PyPI**
   - Prefer token file if present (example `~/.pypi-token`):
   - `TWINE_USERNAME=__token__ TWINE_PASSWORD="$(< ~/.pypi-token)" uv run python -m twine upload dist/*`
   - Verify:
     - `https://pypi.org/project/kon-coding-agent/<version>/`
     - `https://pypi.org/pypi/kon-coding-agent/json` reports latest version

9. **Create GitHub release**
   - If token exists at `~/.github-token`, call Releases API:
   - `POST /repos/<owner>/<repo>/releases` with:
     - `tag_name: v<version>`
     - `target_commitish: main`
     - `name: v<version>`
     - `generate_release_notes: true`
   - If 403 occurs, report missing token scopes/permissions (`contents:write` required)

## Important notes

- **Tagging and GitHub release are separate**:
  - Tag = git ref in repository
  - Release = GitHub object attached to a tag (notes/assets)
- You can do either independently, but most projects do both together for user-facing releases.
- If PyPI publish succeeds but GitHub release fails, do **not** retag/re-publish. Just fix auth and create the release for the existing tag.

## Output checklist to report

- Version bumped in all files
- Checks passed
- Commit hash
- Tag created and pushed
- PyPI upload URL
- GitHub release URL (or exact error + remediation)
