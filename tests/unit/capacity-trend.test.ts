import { describe, expect, it } from "vitest";

import { buildCapacityTrendSummary } from "../../lib/services/capacity-service";
import type { CountyMonthlyTrendPoint } from "../../lib/schemas";

function createPoints(
  previousRatio: number,
  currentRatio: number,
): CountyMonthlyTrendPoint[] {
  return [
    {
      snapshotDate: "2025-07-01",
      childrenCurrentlyInCare: 100,
      currentFosterHomes: 20,
      childrenPerCurrentHome: previousRatio,
    },
    {
      snapshotDate: "2026-07-01",
      childrenCurrentlyInCare: 120,
      currentFosterHomes: 20,
      childrenPerCurrentHome: currentRatio,
    },
  ];
}

describe("buildCapacityTrendSummary", () => {
  it("classifies an increasing trend", () => {
    const summary = buildCapacityTrendSummary(createPoints(5, 6));

    expect(summary.direction).toBe("increasing");
    expect(summary.absoluteChange).toBe(1);
    expect(summary.percentChange).toBeCloseTo(0.2);
  });

  it("classifies a small change as stable", () => {
    const summary = buildCapacityTrendSummary(createPoints(5, 5.2));

    expect(summary.direction).toBe("stable");
  });

  it("classifies a decreasing trend", () => {
    const summary = buildCapacityTrendSummary(createPoints(5, 4));

    expect(summary.direction).toBe("decreasing");
  });
});
