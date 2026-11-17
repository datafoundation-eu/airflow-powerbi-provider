# Releasing airflow-powerbi-provider

Publishing a GitHub Release publishes the package to
[PyPI](https://pypi.org/project/airflow-powerbi-provider/). There is no manual
upload step.

## How it works

1. A GitHub Release is published with a tag such as `v1.2.0`.
2. `.github/workflows/python-publish.yml` starts on the `release: published` event.
3. The workflow builds the sdist and wheel with `python -m build`.
4. `pypa/gh-action-pypi-publish` uploads them to PyPI with
   [trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC). No API
   token is stored in the repository.

The job runs in the GitHub environment `release`. The trusted publisher on PyPI
(project → **Settings** → **Publishing**) must match:

| Setting     | Value                                        |
|-------------|----------------------------------------------|
| Owner/repo  | `datafoundation-eu/airflow-powerbi-provider` |
| Workflow    | `python-publish.yml`                         |
| Environment | `release`                                    |

If any of these change (repo renamed or moved, workflow file renamed, environment
renamed), update the trusted publisher on PyPI first, or the upload fails with
`invalid-publisher`.

> **NOTE:** version 1.1.5 was published from `gschuurman/airflow-powerbi-provider`,
> before the repo moved to `datafoundation-eu`. Before the first release from the
> new location, check that the trusted publisher points to `datafoundation-eu`.
> To see which repo published a version:
>
> ```bash
> curl -s https://pypi.org/integrity/airflow-powerbi-provider/1.1.5/airflow_powerbi_provider-1.1.5-py3-none-any.whl/provenance \
>   | python -c "import json,sys; print([b['publisher'] for b in json.load(sys.stdin)['attestation_bundles']])"
> ```

## Choosing the version number

The project uses [semantic versioning](https://semver.org/):

- **Patch** (`1.1.5` → `1.1.6`): bug fixes, no behaviour change for users.
- **Minor** (`1.1.5` → `1.2.0`): new features, backwards compatible.
- **Major** (`1.1.5` → `2.0.0`): breaking changes, such as removed parameters or a
  new minimum Airflow or Python version.
- **Pre-release** (`1.2.0rc1`): a release candidate to test before the final
  release. pip only installs it when asked for explicitly
  (`pip install airflow-powerbi-provider==1.2.0rc1` or `--pre`).

A version number can be uploaded to PyPI only once. Even a deleted release cannot
reuse its number. If something goes wrong after the upload, release the next patch
version.

## Release steps

### 1. Bump the version

Create a branch from the latest `main`:

```bash
git fetch
git switch -c release/1.2.0 origin/main
```

Set the new version in **both** files:

- `pyproject.toml`: `version = "1.2.0"`
- `src/PowerBI_Operator/provider.yaml`: the entry under `versions:`

`pyproject.toml` decides the version uploaded to PyPI. At runtime,
`get_provider_info()` reports the installed package version to Airflow, so
`provider.yaml` is not used for that. It is kept in sync so the file in the
repository is correct.

The version bump can be part of the feature or fix PR (as in 1.1.4 and 1.1.5) or a
separate PR.

### 2. Test and build locally

```bash
pip install -e . pytest pytest-cov build twine
pytest
python -m build
twine check dist/*
```

Check that:

- all tests pass;
- `dist/` contains `airflow_powerbi_provider-1.2.0.tar.gz` and
  `airflow_powerbi_provider-1.2.0-py3-none-any.whl` with the new version number;
- `twine check` reports `PASSED` for both files.

Delete `dist/` afterwards (`rm -rf dist`). It is not committed.

### 3. Merge to main

Commit, push, and open a pull request:

```bash
git commit -am "Bump version to 1.2.0; <short summary of the change>"
git push -u origin release/1.2.0
```

Wait for the `Python package` workflow (tests on Python 3.10, 3.11 and 3.12) to pass,
then merge the PR.

### 4. Create the GitHub Release

Releases are made from `main` after the merge. The tag is the version with a `v`
prefix (`v1.2.0`).

With the GitHub CLI:

```bash
git fetch
gh release create v1.2.0 --target main --title v1.2.0 --generate-notes
```

For a release candidate, add `--prerelease`:

```bash
gh release create v1.2.0rc1 --target main --title v1.2.0rc1 --generate-notes --prerelease
```

Or in the browser:

1. Open **Releases** → **Draft a new release**.
2. **Choose a tag**: type `v1.2.0` and select **Create new tag on publish**.
3. **Target**: `main`.
4. **Release title**: `v1.2.0`.
5. Click **Generate release notes**, then **Publish release**.

Saving as a draft does not start the publish workflow. Only **Publish release** does.

### 5. Check the publish workflow

```bash
gh run list --workflow python-publish.yml --limit 1
gh run watch <run-id>
```

The run takes about 1 minute. When it succeeds:

- <https://pypi.org/project/airflow-powerbi-provider/> shows the new version;
- `pip index versions airflow-powerbi-provider` lists it (it can take a few
  minutes before pip sees it).

### 6. Verify the installed provider

In a clean virtual environment:

```bash
pip install airflow-powerbi-provider==1.2.0
airflow providers list | grep -i powerbi
```

The listed version must be `1.2.0`.

## Checklist

- [ ] PyPI trusted publisher matches the current repo, workflow and environment
- [ ] Version bumped in `pyproject.toml` and `provider.yaml`
- [ ] `pytest` passes and `python -m build` + `twine check` succeed
- [ ] PR merged to `main`, CI green
- [ ] GitHub Release `vX.Y.Z` published from `main`
- [ ] `python-publish.yml` run succeeded and PyPI shows the version

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Upload fails with `File already exists` / `400 Bad Request` | The version in `pyproject.toml` is already on PyPI. Usually the bump was forgotten. | Bump the version in a new PR, merge, and create a new release. Delete the failed release and its tag (`gh release delete vX.Y.Z --cleanup-tag`). |
| Upload fails with `invalid-publisher` | The trusted publisher on PyPI does not match the repository, workflow file name, or environment. | Fix the trusted publisher under PyPI → project → **Settings** → **Publishing**, then re-run the failed job (`gh run rerun <run-id> --failed`). |
| Publish workflow did not start | The release was saved as a draft, or created by a workflow using `GITHUB_TOKEN` (such events do not trigger other workflows). | Publish the draft, or create the release manually. |
| Wrong commit tagged, not yet on PyPI | The release targeted the wrong branch or commit. | `gh release delete vX.Y.Z --cleanup-tag`, then create the release again from the right commit. |
| Wrong code on PyPI | A broken release was uploaded. | Fix it and release the next patch version. Optionally [yank](https://pypi.org/help/#yanked) the broken version on PyPI so pip skips it. |
