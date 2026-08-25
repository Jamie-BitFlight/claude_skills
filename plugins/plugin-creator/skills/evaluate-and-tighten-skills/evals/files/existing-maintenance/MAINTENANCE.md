# Skill maintenance

## Invariants

- Run-stamp format is fixed-length hex.
  - Owned by: gen_run_stamp.py, concurrency lock, archival cleanup
  - Origin: #142
- Config schema requires a `retries` field with default value 3.
  - Owned by: config.yaml

## Regression provenance

- Rate limiting previously used a hand-rolled token-bucket implementation before the vendor SDK
  added native throttling in the v3 client (migrated in #201). This section is retained from that
  era and no longer describes current behavior.
