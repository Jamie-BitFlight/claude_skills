# Job Event Workflow

This is a reviewed source fixture. Trace its instructions; do not execute or mutate it. The actor's working directory is the directory containing this file.

For job `release-42` at attempt `3`, the publisher command is:

```text
python publisher.py --job-id release-42 --attempt 3
```

Evaluate these independent handoffs in order within their own scenarios:

1. Read `events/latest.json` as the consumer input.
2. Decode the publisher's stdout JSON and pass the resulting event to `consumer.py`.
3. Decode the same JSON and pass the resulting event to `consumer_compatible.py`.
