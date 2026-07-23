# Illinois Foster Home Capacity Explorer

A county-level decision-support application for Illinois DCFS staff.

The product identifies counties where additional foster-home capacity may warrant investigation and uses existing-home engagement as a secondary diagnostic.

## Product focus

- Primary: Foster-home recruitment
- Secondary: Foster-home retention and engagement
- Reporting cutoff: July 1, 2026

## Architecture

```text
Authoritative CSV files
        |
        v
Python ETL and reconciliation
        |
        v
Immutable aggregate SQLite database
        |
        v
Typed repository and service layer
        |
        v
Next.js server components and API routes
        |
        v
React user interface

```

Only aggregate county and statewide data is included in the runtime application. Raw child, placement, and provider records remain build-time inputs.

##Technology

- Next.js App Router
- TypeScript
- React
- Tailwind CSS
- Python
- SQLite
- Zod
- Vitest
- Pytest
- Docker
- Render

## Local development

```powershell
npm install
npm run dev
```