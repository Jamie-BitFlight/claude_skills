# GitLab PyPI Publication Adapter

Evidence: **DOCUMENTATION-VERIFIED, NOT LIVE-TESTED**.

Publish, then authenticate pip with the masked job token and install the exact expected version:

```bash
TWINE_USERNAME=gitlab-ci-token TWINE_PASSWORD="$CI_JOB_TOKEN" \
  python -m twine upload --repository-url \
  "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/pypi" dist/*
PIP_INDEX_URL="https://gitlab-ci-token:${CI_JOB_TOKEN}@${CI_SERVER_HOST}/api/v4/projects/${CI_PROJECT_ID}/packages/pypi/simple" \
  python -m pip install --no-deps "__PACKAGE_NAME__==__PACKAGE_VERSION__"
EXPECTED_NAME="__PACKAGE_NAME__" EXPECTED_VERSION="__PACKAGE_VERSION__" python -c \
  'import importlib.metadata as m, os; assert m.version(os.environ["EXPECTED_NAME"]) == os.environ["EXPECTED_VERSION"]'
```

`CI_JOB_TOKEN` is masked by GitLab. Keep `PIP_INDEX_URL` out of printed diagnostics and do not enable
pip debug output. The metadata assertion proves the installed distribution name resolves to the
exact expected version. Treat duplicate name/version `400 Bad Request` as terminal. Define
durable-link authorization separately.

Apply the composition, tag, and per-destination read-back
[validation gates](./automatic-tag-and-release.md#validation-gates).

SOURCE: <https://docs.gitlab.com/user/packages/pypi_repository/> (accessed 2026-09-22; documentation-verified, not live-tested)
