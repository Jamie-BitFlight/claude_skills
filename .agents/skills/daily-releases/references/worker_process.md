# Daily-release worker process

Read only the supplied task input. Write one JSON artifact to the supplied artifact path,
atomically, containing the supplied task `id`, supplied run identity, and requested analysis. A
retry may have a new attempt identity; write only the artifact for the task supplied in this
invocation. Do not inspect controller state or delegate. Return only `STATUS: DONE` and the artifact path.

For a bucket task, analyze the bucket content into the release-analysis schema. For a synthesis
task, merge the bucket artifacts for that day into the same schema.
