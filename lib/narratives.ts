import type { CountySummary, OpportunityReasonCode } from "./schemas";

export const OPPORTUNITY_REASON_LABELS: Record<OpportunityReasonCode, string> =
  {
    high_children_per_current_home:
      "More children currently in care per licensed foster home",

    high_out_of_county_foster_rate:
      "A larger share of foster-home placements occur outside the removal county",

    high_children_per_preference_matching_home:
      "More current children per home whose preferences overlap the selected age group",

    high_share_without_recent_activity:
      "A larger share of current homes have no recorded foster-home placement activity in the previous 90 days",

    low_median_observed_active_day_rate:
      "Current homes have a lower median share of observed licensed days with an active placement",

    high_renewal_share_90_days:
      "A larger share of current homes have license renewal dates within the next 90 days",
  };

export function getOpportunityReasonLabel(
  code: OpportunityReasonCode,
  selectedAgeBand?: string,
): string {
  if (
    code === "high_children_per_preference_matching_home" &&
    selectedAgeBand
  ) {
    return (
      "More current children per preference-matching " +
      `home for ages ${selectedAgeBand}`
    );
  }

  return OPPORTUNITY_REASON_LABELS[code];
}

export function buildCountyDiagnosis(county: CountySummary): string {
  const countyLabel = `${county.countyName} County`;

  if (
    county.recruitment.level === "limited" &&
    county.engagement.level === "limited"
  ) {
    return (
      `${countyLabel} has limited denominators for both ` +
      "recruitment and existing-home engagement comparisons. " +
      "The available evidence should be reviewed alongside local context."
    );
  }

  switch (county.primaryOpportunity) {
    case "recruitment":
      return (
        `${countyLabel} shows stronger recruitment signals ` +
        "than existing-home engagement signals. Additional " +
        "recruitment may be the more useful area to investigate."
      );

    case "engagement":
      return (
        `${countyLabel} shows stronger existing-home engagement ` +
        "signals than recruitment signals. Staff may want to " +
        "understand current provider availability and support " +
        "needs before relying on recruitment alone."
      );

    case "both":
      return (
        `${countyLabel} shows elevated recruitment and ` +
        "existing-home engagement signals. Both areas may " +
        "warrant further investigation."
      );

    case "review":
      return (
        `${countyLabel} does not show a clear difference between ` +
        "recruitment and existing-home engagement signals. " +
        "Local context may help determine the next area to investigate."
      );
  }
}
