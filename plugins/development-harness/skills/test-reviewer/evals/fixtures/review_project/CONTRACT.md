# Sample application contract

Supported inputs for pricing are nonnegative integer net cents and integer tax percentages.
Invoice totals add tax once to the net amount, rounding the tax down to whole cents.

Publication records an authorization event before any write. An allowed request produces one
write. A denied request raises `PermissionError` and produces no write. The event list records
the externally observed operations in execution order; its entries are the observation boundary.

The encoder produces a JSON object whose `quantity` field is the supplied integer. The consumer
reads that field and returns the same integer. The two functions represent different owners of
the wire contract and may change independently.

This project uses Python 3.11+ and pytest. Run `python -m pytest` in this directory. Tests need no
network, credentials, hardware, or external services. It is a bounded fixture for review, not a
library shipped to a production application.
