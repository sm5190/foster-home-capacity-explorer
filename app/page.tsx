import { CountyPriorityTable } from "../components/county-priority-table";
import { MetricCard } from "../components/metric-card";
import { formatInteger, formatPercentage } from "../lib/formatters";
import { createCapacityService } from "../lib/services";

export default function HomePage() {
  const service = createCapacityService();

  const response = service.getStatewidePriorities();

  const statewide = response.statewide;

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
            Compare county recruitment indicators and open a county brief to
            understand the evidence behind each signal.
          </p>
        </div>

        <div className="data-date">Data as of July 1, 2026</div>
      </section>

      <section aria-labelledby="statewide-summary" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Illinois snapshot</p>

            <h2 id="statewide-summary">Current statewide context</h2>
          </div>
        </div>

        <div className="metric-grid">
          <MetricCard
            detail="Children whose discharge date is not recorded"
            label="Children currently in care"
            value={formatInteger(statewide.childrenCurrentlyInCare)}
          />

          <MetricCard
            detail="Foster homes licensed on the reporting date"
            label="Currently licensed foster homes"
            value={formatInteger(statewide.currentFosterHomes)}
          />

          <MetricCard
            detail="Current placements in licensed foster homes"
            label="Current foster-home placements"
            value={formatInteger(statewide.currentFosterHomePlacements)}
          />

          <MetricCard
            detail={`${formatInteger(
              statewide.localFosterPlacements,
            )} of ${formatInteger(
              statewide.currentFosterHomePlacements,
            )} current foster-home placements`}
            label="Placed in the removal county"
            value={formatPercentage(statewide.localPlacementRate)}
          />
        </div>
      </section>

      <section aria-labelledby="county-priorities" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Recruitment needs</p>

            <h2 id="county-priorities">County priority table</h2>

            <p>
              Counties are ordered by recruitment signal count. Limited-data
              counties remain visible but are not elevated solely by unstable
              percentages.
            </p>
          </div>

          <p className="result-count">
            {formatInteger(response.totalCount)} counties
          </p>
        </div>

        <CountyPriorityTable counties={response.counties} />
      </section>
    </div>
  );
}
