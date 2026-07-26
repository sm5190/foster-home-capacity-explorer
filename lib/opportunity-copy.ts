import type { Focus, OpportunityLevel } from "./schemas";

const FOCUS_LABELS: Record<Focus, string> = {
  recruitment: "recruitment",
  engagement: "existing-home engagement",
};

export function getOpportunityBadgeLabel(
  focus: Focus,
  level: OpportunityLevel,
): string {
  if (level === "review") {
    return "Review local context";
  }

  if (level === "limited") {
    return "Limited data";
  }

  const focusLabel = focus === "recruitment" ? "recruitment" : "engagement";

  return level === "higher"
    ? `Higher ${focusLabel} opportunity`
    : `Possible ${focusLabel} opportunity`;
}

export function getOpportunitySummary(
  focus: Focus,
  level: OpportunityLevel,
): string {
  const focusLabel = FOCUS_LABELS[focus];

  switch (level) {
    case "higher":
      return (
        `Multiple statewide ${focusLabel} indicators crossed ` +
        `the priority thresholds.`
      );

    case "possible":
      return (
        `At least one statewide ${focusLabel} indicator crossed ` +
        `a priority threshold.`
      );

    case "review":
      return (
        `No statewide ${focusLabel} threshold was crossed. ` +
        `Local conditions may still warrant review.`
      );

    case "limited":
      return (
        `Available county data is too limited or unstable for ` +
        `a reliable statewide ${focusLabel} comparison.`
      );
  }
}
