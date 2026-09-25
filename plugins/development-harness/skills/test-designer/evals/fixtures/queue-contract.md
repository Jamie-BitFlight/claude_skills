# Queue API requirement

The proposed API is `enqueue(key, payload)`. A new request creates one job and returns its receipt.
Repeating the same key and payload returns the same receipt without creating another job.
Reusing the key with a different payload is rejected without changing the existing job.

No implementation or tests exist yet. Receipts are opaque strings; their format is not prescribed.
The test environment can observe queued jobs and returned receipts. Plan the next TDD increment
without selecting an unrequested storage technology or writing production code.
