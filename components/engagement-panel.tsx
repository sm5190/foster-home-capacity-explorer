import { formatInteger, formatPercentage } from "../lib/formatters";
import type { CountySummary } from "../lib/schemas";
import { MetricCard } from "./metric-card";

type EngagementPanelProps = {
  county: CountySummary;
};

export function EngagementPanel({ county }: EngagementPanelProps) {
  return (
    <>
      <div className="metric-grid">
        <MetricCard
          detail="Currently licensed homes supporting at least one current placement"
          label="Homes with a current placement"
          value={formatInteger(county.homesWithCurrentPlacement)}
        />

        <MetricCard
          detail="At least one foster-home placement overlapping the previous 90 days"
          label="Homes with recent activity"
          value={formatInteger(county.homesWithRecentActivity)}
        />

        <MetricCard
          detail="No foster-home placement recorded in the previous 90 days"
          label="Homes without recent activity"
          value={formatInteger(county.homesWithoutRecentActivity)}
        />

        <MetricCard
          detail="License end date falls within the next 90 days"
          label="Renewal dates approaching"
          value={formatInteger(county.renewalsWithin90Days)}
        />
      </div>

      <div className="callout">
        <strong>
          Share of observed licensed days with an active placement:
        </strong>{" "}
        {formatPercentage(county.medianObservedActiveDayRate)}
      </div>
    </>
  );
}
