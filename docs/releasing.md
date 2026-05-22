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

On [pypi.org](https://pypi.org):

1. Register the project **`desmosmidi`** (first upload claims the name).
2. **Publishing** → **Add a new trusted publisher** → GitHub:
   - PyPI Project Name: `desmosmidi`
   - Owner: `GXboy12345`
   - Repository name: `DesmosMIDI`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
3. GitHub repo **Settings → Environments**: environment **`pypi`** is created automatically on first release run; no secrets needed for OIDC.

Re-run the failed **pypi** job on the release workflow (or tag `v0.1.1`) after the publisher exists.

Until then, users install from the [GitHub Release wheel](https://github.com/GXboy12345/DesmosMIDI/releases/tag/v0.1.0):

```bash
pip install https://github.com/GXboy12345/DesmosMIDI/releases/download/v0.1.0/desmosmidi-0.1.0-py3-none-any.whl
```

## Version policy

- Tag format: `vMAJOR.MINOR.PATCH` (e.g. `v0.1.0`).
- Pre-1.0: API and export layout may change; document breaking changes in release notes.
