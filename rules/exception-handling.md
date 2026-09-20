# Exception Handling — Narrow Catches Only

Catch only the exceptions the called code is documented to raise. Let all others propagate.

## `except Exception: pass` — Always Prohibited

`BLE001` combined with `S110` (try-except-pass) has no recovery action and no justification in this codebase. Remove the try/except entirely and let the exception propagate.
