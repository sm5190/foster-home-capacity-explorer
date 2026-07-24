import type { Focus, OpportunityLevel } from "../lib/schemas";

type OpportunityBadgeProps = {
  focus: Focus;
  level: OpportunityLevel;
};

const LEVEL_LABELS: Record<Focus, Record<OpportunityLevel, string>> = {
  recruitment: {
    higher: "Higher recruitment opportunity",
    possible: "Possible recruitment opportunity",
    review: "Review local context",
    limited: "Limited data",
  },

  engagement: {
    higher: "Higher engagement opportunity",
    possible: "Possible engagement opportunity",
    review: "Review local context",
    limited: "Limited data",
  },
};

export function OpportunityBadge({ focus, level }: OpportunityBadgeProps) {
  return (
    <span className={`opportunity-badge opportunity-badge--${level}`}>
      {LEVEL_LABELS[focus][level]}
    </span>
  );
}
