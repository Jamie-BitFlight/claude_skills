"""Shared server module loader for frustration-analyzer tests.

Loads server.py once via importlib to avoid fragile sys.path ordering
(in CI the wrong ``server.py`` was resolved first). Test files import
symbols from this module instead of duplicating the loader boilerplate.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp" / "server.py"
_spec = importlib.util.spec_from_file_location("frustration_analyzer_server", _SERVER_PATH)
assert _spec is not None
assert _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

# Re-export commonly used symbols.
render_card = _module._render_card
count_tokens = _module._count_tokens
EncoderCache = _module._EncoderCache
DEFAULT_BATCH_TOKENS = _module._DEFAULT_BATCH_TOKENS
DEFAULT_WIDTH = _module._DEFAULT_WIDTH
DEFAULT_FONT_SIZE = _module._DEFAULT_FONT_SIZE
extract_user_messages = _module.extract_user_messages

# Shared test constants for render tests.
TASK = "Implement login page"
ASSISTANT = "I have written the login page using React."
USER = "I said use Vue, not React! Read the prompt!"
