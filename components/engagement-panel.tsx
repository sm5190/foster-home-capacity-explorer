import { formatInteger, formatPercentage } from "../lib/formatters";

import type { CountySummary } from "../lib/schemas";
import { MetricCard } from "./metric-card";

type EngagementPanelProps = {
  county: CountySummary;
};

export function EngagementPanel({ county }: EngagementPanelProps) {
  const renewalIntersectionShare =
    county.renewalsWithin90Days > 0
      ? county.renewalsWithoutRecentActivity / county.renewalsWithin90Days
      : null;

  return (
    <>
      <div className="metric-grid">
        <MetricCard
          label="Current foster homes"
          value={formatInteger(county.currentFosterHomes)}
          detail={`${formatInteger(
            county.homesWithCurrentPlacement,
          )} supporting a current placement`}
        />

        <MetricCard
          label="No recent placement activity"
          value={formatInteger(county.homesWithoutRecentActivity)}
          detail="No recorded foster-home placement activity in the previous 90 days"
        />

        <MetricCard
          label="Renewal dates within 90 days"
          value={formatInteger(county.renewalsWithin90Days)}
          detail="A renewal date is not a prediction of closure"
        />

        <MetricCard
          label="Renewing + no recent activity"
          value={formatInteger(county.renewalsWithoutRecentActivity)}
          detail={
            renewalIntersectionShare === null
              ? "No upcoming renewals"
              : `${formatPercentage(
                  renewalIntersectionShare,
                )} of upcoming renewals`
          }
        />
      </div>

      {county.renewalsWithoutRecentActivity > 0 ? (
        <div className="callout engagement-callout">
          <strong>
            {formatInteger(county.renewalsWithoutRecentActivity)} of{" "}
            {formatInteger(county.renewalsWithin90Days)} homes with renewal
            dates in the next 90 days also have no recent recorded placement
            activity.
          </strong>

          <span>
            This intersection may warrant closer review when planning renewal
            outreach and provider support.
          </span>
        </div>
      ) : null}

      <p className="method-note">
        Median share of observed licensed days with an active placement:{" "}
        {formatPercentage(county.medianObservedActiveDayRate)}
      </p>
    </>
  );
}
