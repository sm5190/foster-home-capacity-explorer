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


## County placement-setting aggregates

**Status:** Accepted  
**Date:** July 23, 2026  
**Database schema:** 1.2

The County Capacity Brief requires a current placement-setting breakdown for kin, foster-home, and nonfamily placements.

The original aggregate `county_summary` table stored only the foster-home count. Schema version 1.2 adds `current_kin_placements` and `current_nonfamily_placements`.

These fields belong in `county_summary` rather than a separate table because each measure has exactly one value per county and reporting snapshot.

Database constraints and ETL validation require:

- kin + foster home + nonfamily = children currently in care
- local foster home + out-of-county foster home = all foster-home placements

The serving database remains aggregate-only and contains no child or provider identifiers.

## Historical county capacity trend

The county brief includes 13 monthly snapshots from July 1, 2025
through July 1, 2026.

Each point calculates children currently in care from the county
divided by foster homes licensed in the county on that date.

The trend is described as a capacity-pressure indicator, not as
available foster-home beds.

A change smaller than 5 percent is displayed as broadly stable.

## Renewal plus no recent activity

The application separately identifies currently licensed homes
whose license end date is within 90 days and that have no recorded
foster-home placement activity during the previous 90 days.

The metric is used as outreach evidence. It is not treated as a
prediction of non-renewal or closure.