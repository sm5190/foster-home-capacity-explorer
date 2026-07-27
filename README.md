# Illinois Foster Home Capacity Explorer

A public county-level analytical application for exploring foster-home
recruitment, retention, and engagement signals across Illinois.

## Live application

**Production:** https://foster-home-capacity-explorer.onrender.com/

**Repository:** https://github.com/sm5190/foster-home-capacity-explorer

**Data as of:** July 1, 2026

## Product purpose

The application helps nontechnical staff answer two related questions:

1. Where could additional foster-home recruitment make the greatest difference?
2. Where may existing licensed homes warrant further engagement or retention
   review?

Recruitment is the primary workflow. Existing-home engagement is a secondary
view within the same county-capacity workflow.

Opportunity labels are analytical signals created for this application. They are
not official Illinois DCFS grades or determinations.

## Main features

- Statewide recruitment and engagement views
- Searchable and sortable 102-county comparison table
- Interactive Illinois county map
- County Capacity Briefs with direct URLs
- Current child and foster-home measures
- Local and out-of-county placement context
- Current placement-setting breakdown
- Age-preference alignment
- Existing-home activity and renewal indicators
- Renewal plus no-recent-activity intersection
- Thirteen monthly capacity-pressure snapshots
- Deterministic questions for local investigation
- Print-friendly county briefs
- Public health endpoint

## Data sources

The controlled local pipeline uses:

- `child_level.csv`
- `placement_level.csv`
- `provider_level_updated.csv`

The corrected provider source excludes nonfamily providers that were not
intended to be included in foster-home supply measures.

Raw child, placement, and provider records are not committed to the public
repository and are not copied into the production image.

## Locked analytical dates

- Observation start: January 1, 2022
- Reporting cutoff: July 1, 2026
- Recent activity window: 90 days
- Renewal review window: 90 days
- Historical trend: July 2025 through July 2026

## Key statewide values

- Children currently in care: 8,071
- Currently licensed foster homes: 3,395
- Foster homes without recent placement activity: 225
- Renewal dates within 90 days: 1,457
- Renewing within 90 days and without recent activity: 184
- Illinois counties represented: 102

## Metric interpretation

### Children per current foster home

Current children in care divided by currently licensed foster homes in the
county.

This is a pressure indicator, not a count of children waiting for placement or
a measure of available beds.

### Local foster-home placement rate

The percentage of current foster-home placements in which the placement county
matches the child's removal county.

The interface displays the numerator and denominator because percentages can be
unstable for counties with small placement counts.

### Recent placement activity

A provider has recent activity when a qualifying foster-home placement overlaps
the 90-day period ending on the reporting cutoff.

No recent activity does not imply unwillingness, poor performance, or unused
licensed capacity.

### Observed active-day rate

Observed days with a qualifying foster-home placement divided by observed
licensed days during the analysis window.

### Renewal dates within 90 days

Current foster homes whose recorded licence renewal date falls within 90 days
after the reporting cutoff.

A renewal date is not interpreted as a closure date.

### Age-preference alignment

Current children in each age band are compared with current provider age
preferences that overlap that band.

Provider preferences do not represent available beds.

### Capacity pressure over time

The historical line chart shows children currently in care per current licensed
foster home for 13 monthly snapshots.

The trend is descriptive and is not a forecast or causal analysis.

## Opportunity labels

- **Higher opportunity:** multiple statewide indicators cross the configured
  thresholds.
- **Possible opportunity:** at least one statewide indicator crosses a
  threshold.
- **No elevated signal:** the county does not cross the statewide thresholds,
  although local conditions may still warrant review.
- **Limited data:** available denominators are too small or unstable for a
  reliable comparison.

The thresholds are product-defined analytical rules, not official policy.

## Architecture

```text
Controlled raw CSV files
        |
        v
Python validation and ETL
        |
        v
Versioned aggregate SQLite database
        |
        v
Typed repository layer
        |
        v
Next.js server components and API routes
        |
        v
Docker standalone production image
        |
        v
Render web service

```

## Why SQLite

The product serves a periodic, immutable, read-only county snapshot.

All expensive calculations are completed offline, and runtime requests perform
small indexed aggregate queries. SQLite provides a simple and reproducible
deployment artifact without requiring an external database service.

### Privacy boundary

The production runtime contains only:

```text
/app/data/generated/foster_capacity.db
```

It contains county and statewide aggregates and no child or provider identifier
columns.

## Technology
- Next.js
- React
- TypeScript
- Python
- SQLite
- D3 geographic projection
- Vitest
- Pytest
- Docker
- GitHub Actions
- Render
## Local setup
Requirements: 

- Node.js 22
- npm
- Python 3.12
- uv
- Docker Desktop

### install dependencies: 
```bash
npm ci
uv pip install --requirement requirements.txt
```
### Add controlled source files
Place these files in data/raw:

```text
data/raw/child_level.csv
data/raw/placement_level.csv
data/raw/provider_level_updated.csv
```

Do not commit them.

### Build the aggregate database:
```bash
uv run python -m scripts.build_database
```

### Generate the Illinois map asset:
```bash
npm run map:build
```
### Start development mode:
```bash
npm run dev

```

Open:
```text
http://localhost:3000

```
## Quality checks:

### Full local Python suite

The full Python suite requires the controlled raw files:
```bash
uv run pytest
```
### Web quality gate:
```bash
npm run check
```
### Production smoke test

Start the application or container, then run:
```bash
npm run smoke
```
## Docker

### Build:

```bash
docker build `
  --tag foster-home-capacity-explorer `
  .
```

### Run:
```bash
docker run `
  --rm `
  --publish 3000:3000 `
  foster-home-capacity-explorer
```

### Open:

```text
http://localhost:3000

```
### Health endpoint: 
```text
GET /api/health
```
The response reports application status, aggregate schema version, observation
start, reporting cutoff, and build status.

## Deployment

Render builds the root Dockerfile using the configuration in render.yaml.

The service:

- binds to 0.0.0.0,
- uses the platform-provided port,
- checks /api/health,
- runs as a non-root user,
- requires no persistent disk,
- requires no external database.

Render's free service tier may take additional time to respond after an idle
period.

## Repository structure:


```text
app/                         Next.js routes and API handlers
components/                  Reusable interface components
db/                          Versioned SQLite schemas
docs/                        Decisions and review evidence
lib/                         Contracts, repositories, services, and map data
scripts/                     Python ETL and build tooling
tests/                       Python and TypeScript tests
data/generated/              Validated public aggregate artifacts
Dockerfile                   Multi-stage production image
render.yaml                  Render Blueprint
```


## Assumptions and limitations

- Source records are treated as authoritative for the take-home exercise.
- Meaningful null values are preserved.
- Child ages are not imputed.
- Provider preferences are not interpreted as availability.
- Renewal dates are not interpreted as closures.
- Out-of-county placement patterns do not establish causation.
- Opportunity labels identify questions to investigate rather than prescribed
  actions.
- The application is an analytical snapshot, not a live placement-management
system.

## Decision log

See the [Decision Log](docs/decision-log.md).

## Release

Final submission tag:
```text
submission-v1.0
```
