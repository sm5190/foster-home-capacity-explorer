import Link from "next/link";
import { CountyPriorityTable } from "../components/county-priority-table";
import { MetricCard } from "../components/metric-card";
import { StatewideControls } from "../components/statewide-controls";
import {
  parseCountyListSearchParams,
  type RawSearchParams,
} from "../lib/county-query";
import { formatInteger, formatPercentage } from "../lib/formatters";
import { createCapacityService } from "../lib/services";

type HomePageProps = {
  searchParams: Promise<RawSearchParams>;
};

const AGE_LABELS = {
  all: "all ages",
  "0-5": "ages 0 to 5",
  "6-12": "ages 6 to 12",
  "13-17": "ages 13 to 17",
} as const;

export default async function HomePage({ searchParams }: HomePageProps) {
  const rawSearchParams = await searchParams;

  const { query, invalidQuery } = parseCountyListSearchParams(rawSearchParams);

  const service = createCapacityService();

  const response = service.getStatewidePriorities(query);

  const statewide = response.statewide;

  const focusLabel =
    query.focus === "recruitment" ? "Recruitment" : "Existing-home engagement";

  return (
    <div className="page-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Statewide priorities</p>

          <h1>
            Where could additional foster-home capacity make the greatest
            difference?
          </h1>

          <p className="hero__description">
            Compare county recruitment and existing-home engagement indicators,
            then open a county brief to inspect the evidence.
          </p>
        </div>

        <div className="data-date">Data as of July 1, 2026</div>
      </section>

      {invalidQuery ? (
        <div className="notice" role="status">
          One or more URL filters were invalid, so the default filters were
          restored.
        </div>
      ) : null}

      <section aria-labelledby="statewide-controls" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Explore counties</p>

            <h2 id="statewide-controls">Filter and compare</h2>
          </div>
        </div>

        <StatewideControls query={response.query} />
      </section>

      <section aria-labelledby="statewide-summary" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Illinois snapshot</p>

            <h2 id="statewide-summary">Current statewide context</h2>
          </div>
        </div>

        <div className="metric-grid">
          {query.focus === "recruitment" ? (
            <>
              <MetricCard
                label="Children currently in care"
                value={formatInteger(statewide.childrenCurrentlyInCare)}
              />

              <MetricCard
                label="Currently licensed foster homes"
                value={formatInteger(statewide.currentFosterHomes)}
              />

              <MetricCard
                label="Current foster-home placements"
                value={formatInteger(statewide.currentFosterHomePlacements)}
              />

              <MetricCard
                label="Placed within removal county"
                value={formatPercentage(statewide.localPlacementRate)}
                detail={`${formatInteger(
                  statewide.localFosterPlacements,
                )} of ${formatInteger(
                  statewide.currentFosterHomePlacements,
                )} foster-home placements`}
              />
            </>
          ) : (
            <>
              <MetricCard
                label="Currently licensed foster homes"
                value={formatInteger(statewide.currentFosterHomes)}
              />

              <MetricCard
                label="No recent placement activity"
                value={formatInteger(statewide.homesWithoutRecentActivity)}
              />

              <MetricCard
                label="Renewal dates within 90 days"
                value={formatInteger(statewide.renewalsWithin90Days)}
              />

              <MetricCard
                label="Renewing + no recent activity"
                value={formatInteger(statewide.renewalsWithoutRecentActivity)}
              />
            </>
          )}
        </div>
      </section>

      <section aria-labelledby="county-priorities" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{focusLabel}</p>

            <h2>
              {query.focus === "recruitment"
                ? "Recruitment priorities by county"
                : "Retention and engagement priorities by county"}
            </h2>

            <p>
              Showing {focusLabel.toLowerCase()} indicators for{" "}
              {AGE_LABELS[query.age]}. Limited-data counties remain visible but
              are not elevated solely by unstable percentages.
            </p>
          </div>

          <p className="result-count">
            {formatInteger(response.totalCount)}{" "}
            {response.totalCount === 1 ? "county" : "counties"}
          </p>
        </div>

        {response.counties.length > 0 ? (
          <CountyPriorityTable
            counties={response.counties}
            focus={query.focus}
            query={response.query}
          />
        ) : (
          <div className="empty-table-state">
            <h3>No counties match the current search</h3>

            <p>Try a broader county name or reset the current filters.</p>

            <Link className="button button--primary" href="/">
              Reset filters
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
