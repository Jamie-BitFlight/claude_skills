#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.0"]
# ///
"""Minimal PEP 723 script used only to exercise ty's script-scoped environment resolution.

Not meant to be executed for its own sake -- see `tests/test_ty_pep723_environment.py`. `typer` is
already declared in this repo's root `[dependency-groups] dev` group (every PEP 723 script's
dependencies are mirrored there per `rules/python-development.md`, solely so `ty` and the IDE/LSP
can resolve them), so the project `.venv` always satisfies this import when ty resolves the
project's environment correctly for this file.

Kept deliberately trivial and side-effect free: this file exists to have a PEP 723 metadata block
and one third-party import, nothing more.
"""

from __future__ import annotations

import typer

_TYPER_APP_FACTORY = typer.Typer
