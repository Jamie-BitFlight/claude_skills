# Data Format Selection

Pick the data format closest to the consumer. The consumer is whatever code reads the data, not
whoever reads the file.

| The data is... | Format |
|---|---|
| Static, and every consumer is Python | A `.py` module holding typed data (Pydantic rows in a module-level tuple or mapping) |
| Static, small, and read by more than one language (Python + JS, a hook + a script) | `.json` |
| Written or queried at runtime, by more than one consumer | SQLite |

## Never parse prose for data

Never author a data table as prose and then parse the prose to get the data back. Writing a
markdown or AST parser to read your own repository's data means the data is in the wrong format —
move the data, do not improve the parser.

This is separate from [Markdown AST Parsing](.claude/CLAUDE.md): `marko` is still the only way
to parse markdown you do not own. It is never the way to reach data you wrote yourself.

## A document describes data; it never copies it

A document that must describe the data does exactly one of two things:

- **Names the source file** — links to it, states the rules governing it, and holds no copy of its
  contents; or
- **Is generated from it** by a real generator (mkdocs or equivalent), and is not hand-edited.

A hand-maintained copy alongside the source is forbidden. A drift test policing such a copy is a
symptom, not a fix — delete the copy instead of testing it.

## Worked example: the artifact-type registry

**What it was**: `plugins/development-harness/docs/artifact-registry.md` carried the map of
artifact types to their permitted registering agents as a markdown table.
`plugins/development-harness/dh_core/artifact_registry.py` parsed that table at runtime through the
marko GFM AST, locating it by heading name and reading its columns by header text.

**Why it was wrong**: every consumer was Python — the decomposition-exit gate and two test modules.
The map's real shape (a type, a set of agents, a boolean) reached them through a document parse
that could fail in ways nothing else could: the heading anchor and the header-row anchor drifted
apart once, and the gate silently resolved zero artifact types while the suite stayed green. Type
membership in `ArtifactType` needed a drift test because the parser produced strings.

**What it became**: `dh_core/artifact_registry.py` holds `REGISTRY`, a tuple of Pydantic rows whose
`artifact_type` field is an `ArtifactType` member. A row naming a non-member fails at import, so
the drift test that policed membership is gone along with the parser, the locator constants, and
the error class for "the registry is not where I said it is". The document keeps the ownership
rules and names the module; it holds no copy of the map.
