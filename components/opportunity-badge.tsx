import { getOpportunityBadgeLabel } from "../lib/opportunity-copy";

import type { Focus, OpportunityLevel } from "../lib/schemas";

type OpportunityBadgeProps = {
  focus: Focus;
  level: OpportunityLevel;
};

export function OpportunityBadge({ focus, level }: OpportunityBadgeProps) {
  return (
    <span
      className={["opportunity-badge", `opportunity-badge--${level}`].join(" ")}
    >
      {getOpportunityBadgeLabel(focus, level)}
    </span>
  );
}
