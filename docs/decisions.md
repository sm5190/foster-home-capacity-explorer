# Architecture Decision Log

## Runtime aggregate artifact contract

**Status:** Accepted  
**Date:** July 23, 2026

The production application requires a validated aggregate SQLite database at runtime. The authoritative child-level, placement-level, and provider-level CSV files remain build-time only and must not be included in the public application or runtime container.

The repository tracks only these validated aggregate runtime artifacts:

- `data/generated/foster_capacity.db`
- `data/generated/metadata.json`
- `data/generated/county-summary.csv`

The raw files under `data/raw/` remain ignored. The Python ETL pipeline is the only supported mechanism for regenerating the aggregate artifacts.

Before publication, the ETL validates database integrity, foreign keys, aggregate reconciliation, approved public tables, forbidden identifier columns, CSV row counts, and artifact checksums.

The aggregate SQLite database is immutable and will be opened read-only by the Next.js server.