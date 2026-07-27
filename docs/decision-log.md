# Foster Home Capacity Explorer: Decision Log

## Product scope

### Recruitment is the primary workflow

The application primarily helps staff identify counties where additional
foster-home recruitment may warrant investigation.

Existing-home engagement is presented as a secondary workflow using the same
county comparison and county brief structure.

This avoids creating two disconnected products and keeps the experience focused
on one county-capacity decision workflow.

### Opportunity labels are analytical signals

The labels Higher opportunity, Possible opportunity, No elevated signal, and
Limited data are product-defined analytical classifications.

They are not official Illinois DCFS grades, policies, or determinations. County
labels should be used to decide what to investigate, not as conclusions about
county performance.

## Data decisions

### Corrected provider source

The analysis uses `provider_level_updated.csv`.

The corrected provider file excludes nonfamily providers that were not intended
to be included in foster-home supply measures.

Nonfamily placements remain represented in child placement-setting analysis,
but they are excluded from licensed foster-home supply metrics.

### Reporting cutoff

The reporting cutoff is July 1, 2026.

The analysis window begins January 1, 2022.

All current-state metrics and historical snapshots are calculated relative to
the locked reporting cutoff.

### County canonicalisation

The source spelling `Vermillion` is mapped to the canonical Illinois county name
`Vermilion`.

This produces a complete set of 102 Illinois counties and prevents duplicate
county records across the aggregate database and map.

### Meaningful nulls

Missing age values and undefined percentages remain null.

The pipeline does not impute child ages or convert unavailable percentages to
zero.

### Provider preferences are not capacity

Age preferences describe the ages a provider is licensed or willing to
consider. They do not represent an available bed, immediate placement capacity,
or guaranteed acceptance.

## Analytical decisions

### Recruitment evidence

Recruitment evidence combines:

- children currently in care,
- currently licensed foster homes,
- children per current foster home,
- current local and out-of-county foster-home placements,
- age-band alignment between current children and current provider preferences.

Small-number guardrails prevent unstable percentages from creating elevated
opportunity labels.

### Existing-home engagement evidence

Engagement evidence combines:

- current foster homes,
- homes with and without recent placement activity,
- median observed active-day rate,
- renewal dates within 90 days,
- homes that both renew within 90 days and show no recent placement activity.

A renewal date is not treated as an expected closure.

No recent placement activity is not interpreted as provider unwillingness or
inactivity outside the available placement data.

### Historical trend

The county pressure chart contains 13 monthly snapshots from July 2025 through
July 2026.

It shows children currently in care per current licensed foster home at each
snapshot date.

The trend is descriptive and is not evidence of causation.

### County map

The map is an interactive geographic view of the same classifications used in
the county table.

Every Illinois county remains visible for statewide context. Map colours are
analytical signals rather than official geographic grades.

The table remains the precise comparison and accessibility fallback.

## Architecture decisions

### Precomputed aggregate pipeline

Expensive transformations are completed offline in Python.

The public application does not parse raw child, placement, or provider CSV
files at request time.

### Embedded SQLite

The application uses a versioned, immutable aggregate SQLite database.

SQLite is appropriate because the application serves a periodic, read-only
county-level snapshot with a small query workload.

A managed database would add operational complexity without providing a
meaningful benefit for the current scale.

### Repository layer

Application code accesses SQLite through typed repository interfaces and
parameterised queries.

UI components do not execute SQL directly.

### Privacy boundary

Raw child-level, placement-level, and provider-level records are excluded from:

- the public repository,
- public web assets,
- the production Docker image,
- client responses.

The production image contains only the validated aggregate SQLite database.

### Docker and Render

The production image uses a multi-stage Docker build, Next.js standalone output,
and a non-root runtime user.

Render deploys the Docker image and uses `/api/health` as the service health
check.

### Public CI limitation

The private raw source CSVs are intentionally absent from GitHub Actions.

Local development runs the complete ETL and Python suite with the controlled
source files.

Public CI runs privacy-safe Python tests and validates the committed aggregate
database, schema version, integrity, row counts, map reconciliation, web build,
Docker image, health endpoint, and production smoke tests.

## Known limitations

- Provider preferences do not measure open beds.
- A renewal date does not imply an imminent closure.
- No recent placement activity does not explain why a home has not received a
  recent placement.
- Out-of-county placement patterns do not establish causation.
- County percentages may be unstable when denominators are small.
- The application provides an analytical snapshot rather than a live operational
  placement system.
- The application does not include case-level or provider-level workflows.
- The historical trend covers 13 monthly snapshots and is not a forecasting
  model.