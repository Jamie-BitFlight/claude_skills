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

This is separate from `marko` guidance in [AGENTS.md](AGENTS.md): `marko` is still the only way
to parse markdown you do not own. It is never the way to reach data you wrote yourself.

## A document describes data; it never copies it

A document that must describe the data does exactly one of two things:

- **Names the source file** — links to it, states the rules governing it, and holds no copy of its
  contents; or
- **Is generated from it** by a real generator (mkdocs or equivalent), and is not hand-edited.

A hand-maintained copy alongside the source is forbidden. A drift test policing such a copy is a
symptom, not a fix — delete the copy instead of testing it.
