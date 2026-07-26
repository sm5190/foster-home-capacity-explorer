import { MetricCard } from "../components/metric-card";
import { StatewideControls } from "../components/statewide-controls";
import { StatewideCountyExplorer } from "../components/statewide-county-explorer";

import {
  parseCountyListSearchParams,
  type RawSearchParams,
} from "../lib/county-query";

import { formatInteger, formatPercentage } from "../lib/formatters";

import { createCapacityService } from "../lib/services";

type HomePageProps = {
  searchParams: Promise<RawSearchParams>;
};

export default async function HomePage({ searchParams }: HomePageProps) {
  const rawSearchParams = await searchParams;

  const { query, invalidQuery } = parseCountyListSearchParams(rawSearchParams);

  const service = createCapacityService();

  const response = service.getStatewidePriorities(query);

  const statewide = response.statewide;

  const mapCounties =
    query.search.length === 0
      ? response.counties
      : service.getStatewidePriorities({
          ...query,
          search: "",
          sort: "county",
          direction: "asc",
        }).counties;

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
                detail={`${formatInteger(
                  statewide.localFosterPlacements,
                )} of ${formatInteger(
                  statewide.currentFosterHomePlacements,
                )} foster-home placements`}
                label="Placed near home community"
                value={formatPercentage(statewide.localPlacementRate)}
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

      <StatewideCountyExplorer
        counties={response.counties}
        mapCounties={mapCounties}
        query={response.query}
        totalCount={response.totalCount}
      />
    </div>
  );
}
