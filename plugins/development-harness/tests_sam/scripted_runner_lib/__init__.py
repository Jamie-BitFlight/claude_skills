"""The modules ``scripted_runner.py`` is built from, so no one file of it grows past a single read.

``scripted_runner.py`` is the entry script and the only file that carries the shebang and the
``# /// script`` block; everything here is a plain module, which is how ``rules/python-development.md``
says a PEP 723 script is split. That block still governs the whole runner's PyPI dependencies,
because it is the only file ``uv`` is ever pointed at.

The runner's source-reading tests derive the set of files they scan from
``workspace.LIBRARY_DIRECTORY`` rather than listing it, so a module added here is scanned the
moment it lands.
"""

from __future__ import annotations
