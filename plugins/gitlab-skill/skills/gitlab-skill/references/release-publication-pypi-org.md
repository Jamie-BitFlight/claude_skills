# PyPI.org Publication Adapter

Evidence: **DOCUMENTATION-VERIFIED, NOT LIVE-TESTED**.

For GitLab.com trusted publishing, configure the publisher and `PYPI_ID_TOKEN` audience `pypi`.
For self-managed GitLab, use a minimum-project-scope PyPI API token with username `__token__` and
the complete `pypi-` password. Publish with the project's Twine command, then read back:

```bash
python -m twine upload dist/*
python -m pip index versions "__PACKAGE_NAME__" --index-url https://pypi.org/simple
```

Define any Release link separately.

Apply the composition, tag, and per-destination read-back
[validation gates](./automatic-tag-and-release.md#validation-gates).

SOURCE: <https://docs.pypi.org/trusted-publishers/using-a-publisher/> (accessed 2026-09-22; documentation-verified, not live-tested)
