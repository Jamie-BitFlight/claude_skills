---
name: synchronize-documentation
description: Synchronize existing documentation with an observed code/configuration/API change while preserving each document's purpose and authority. Use after implementation changes can make documentation stale, incomplete, or internally inconsistent.
---
# Synchronize Documentation

Update only documentation whose truth or required coverage changed.

1. Establish the exact implementation delta and externally/user/maintainer-visible consequences.
2. Discover documentation by semantic relationship to the changed contracts, names, paths, configuration, APIs, and workflows. Do not sweep every document without a reason it could be affected.
3. For each candidate document, determine its purpose, audience, authority, and source-of-truth relationship before editing.
4. Compare its material claims with the current implementation/contract. Skip unaffected documents explicitly.
5. Update the narrowest authoritative location. Remove stale claims rather than preserving history inline unless the document's purpose is historical.
6. When several documents duplicate one meaning, consolidate toward the authoritative source and keep navigation pointers where needed.
7. Preserve examples when they are useful executable/user guidance; update or test them rather than banning code examples categorically.
8. Re-read edited documents, validate links/references and repository-required checks, and report changed and examined-but-unchanged surfaces.

Do not modify source behavior as part of documentation synchronization. Do not assume implementation outranks a normative specification; escalate an authority conflict instead of rewriting the specification to match code.
