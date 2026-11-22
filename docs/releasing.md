# Releasing

This project is released to [PyPI as `cpp-coverage`](https://pypi.org/project/cpp-coverage/) by the [Release workflow](../.github/workflows/release.yml). The workflow is triggered by pushing a tag matching `v*`, and it:

1. Builds the sdist and wheel with `python -m build`.
2. Publishes the distributions to PyPI using a [trusted publisher](https://docs.pypi.org/trusted-publishers/) (GitHub environment `pypi`, no API token required).
3. Creates a GitHub Release for the tag with auto-generated notes and the distributions attached.

## Prerequisites

- Push access to `AndrewJSender/coverage-analytics`.
- A PyPI trusted publisher configured for this repository and the `release.yml` workflow, bound to the `pypi` environment (one-time setup).
- A clean checkout of `main` with CI passing.

## Release version

Set the version being released once:

```zsh
export release_version=0.2.0
```

Use [semantic versioning](https://semver.org/): bump the minor version for new features, the patch version for fixes.

## Scripted release

The steps below are automated by [src/release.py](../src/release.py), which bumps the version, commits, tags, and pushes:

```zsh
python3 src/release.py "$release_version"
```

Then continue from [step 5](#5-watch-the-workflow) to monitor and verify the release.
If the script fails, inspect the working tree, commit, tag, and remote before
retrying; a failure may occur after some steps have already completed.

## Manual release steps

### 1. Update the version

Set the `version` field in [pyproject.toml](../pyproject.toml):

```zsh
sed -i '' -E "s/^version = \".*\"/version = \"$release_version\"/" pyproject.toml
```

### 2. Verify the release locally (optional but recommended)

```zsh
# Run the test suite
python -m pytest tests

# Build the distributions the same way the workflow does
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Clean up the local build output afterwards:

```zsh
rm -rf dist/
```

### 3. Commit and push the version bump

```zsh
git checkout main
git pull
git add pyproject.toml
git commit -m "Release $release_version"
git push origin main
```

### 4. Tag the release and push the tag

The tag must start with `v` and should match the version in `pyproject.toml`:

```zsh
git tag "v$release_version"
git push origin "v$release_version"
```

Pushing the tag triggers the Release workflow.

### 5. Watch the workflow

```zsh
gh run watch --repo AndrewJSender/coverage-analytics
```

Or list recent runs:

```zsh
gh run list --repo AndrewJSender/coverage-analytics --workflow release.yml
```

### 6. Verify the release

```zsh
# Confirm the GitHub Release exists
gh release view "v$release_version" --repo AndrewJSender/coverage-analytics

# Confirm the new version installs from PyPI (may take a minute to appear)
pip install --upgrade cpp-coverage
coverage-analytics --help
```

## Fixing a bad release

- PyPI does not allow re-uploading a version. If a release is broken, bump the patch version and release again.
- To remove a bad tag and GitHub Release:

```zsh
gh release delete "v$release_version" --repo AndrewJSender/coverage-analytics
git push origin --delete "v$release_version"
git tag -d "v$release_version"
```
