# Releasing DesmosMIDI

## Consumer install paths

| Channel | Command |
| --- | --- |
| PyPI (after first release) | `pip install desmosmidi` |
| GitHub Release wheel | download `desmosmidi-*-py3-none-any.whl`, then `pip install desmosmidi-*.whl` |
| From clone | `pip install -e ".[dev]"` for development |

Then: `desmosmidi setup` (Desmos API key in `.env` in the working directory).

## Maintainer: cut a release

1. Bump `version` in `pyproject.toml` and `src/desmosmidi/__init__.py` (keep in sync).
2. Run `pytest` and `hatch build` locally.
3. Commit, tag, push:
   ```bash
   git tag v0.1.0
   git push origin master --tags
   ```
4. GitHub Actions workflow **release** uploads `dist/*` to the GitHub Release and publishes to PyPI.

## PyPI trusted publishing (one-time)

On [pypi.org](https://pypi.org) (create `desmosmidi` project if needed):

1. **Publishing** → add a trusted publisher:
   - Owner: your GitHub user or org
   - Repository: `DesmosMIDI` (or actual repo name)
   - Workflow: `release.yml`
   - Environment: `pypi` (matches the workflow `environment: pypi`)

2. In the GitHub repo: **Settings → Environments** → create **`pypi`** (no secrets required for trusted publishing).

If PyPI publish fails on first tag, the GitHub Release assets (wheel + sdist) are still attached; users can `pip install` the wheel from the release page.

## Version policy

- Tag format: `vMAJOR.MINOR.PATCH` (e.g. `v0.1.0`).
- Pre-1.0: API and export layout may change; document breaking changes in release notes.
