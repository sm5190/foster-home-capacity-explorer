import { describe, expect, it } from "vitest";

import {
  apiErrorResponseSchema,
  countyDetailResponseSchema,
  countyListQuerySchema,
  countyListResponseSchema,
  countyPlacementSettingsSchema,
  countyRouteParamsSchema,
  countySummarySchema,
  healthResponseSchema,
} from "../../lib/schemas";

const metadataFixture = {
  schemaVersion: "1.3",
  reportingCutoff: "2026-07-01",
  observationStart: "2022-01-01",
  buildStatus: "complete" as const,
};

const opportunityFixture = {
  level: "possible" as const,
  signalCount: 1,
  reasons: [
    {
      code: "high_children_per_current_home" as const,
      label: "More children currently in care per licensed home",
      value: 8.2,
      threshold: 6.5,
    },
  ],
};

const countyFixture = {
  countySlug: "example",
  countyName: "Example",

  childrenCurrentlyInCare: 120,
  currentFosterHomes: 20,
  childrenPerCurrentHome: 6,

  currentFosterPlacements: 60,
  localFosterPlacements: 20,
  outOfCountyFosterPlacements: 40,
  localPlacementRate: 1 / 3,

  homesWithCurrentPlacement: 15,
  homesWithRecentActivity: 18,
  homesWithoutRecentActivity: 2,
  medianObservedActiveDayRate: 0.7,
  renewalsWithin90Days: 4,
  renewalsWithoutRecentActivity: 0,

  recruitment: opportunityFixture,
  engagement: {
    level: "review" as const,
    signalCount: 0,
    reasons: [],
  },

  primaryOpportunity: "recruitment" as const,
  limitedData: false,
};

const statewideFixture = {
  reportingCutoff: "2026-07-01",
  observationStart: "2022-01-01",

  childrenCurrentlyInCare: 8_071,

  currentKinPlacements: 3_688,
  currentFosterHomePlacements: 4_343,
  currentNonfamilyPlacements: 40,

  currentFosterHomes: 3_395,
  homesWithCurrentPlacement: 2_733,
  homesWithRecentActivity: 3_170,
  homesWithoutRecentActivity: 225,
  renewalsWithin90Days: 0,
  renewalsWithoutRecentActivity: 0,

  localFosterPlacements: 1_519,
  outOfCountyFosterPlacements: 2_824,
  localPlacementRate: 1_519 / 4_343,

  medianObservedActiveDayRate: 0.697,
};

describe("county list query schema", () => {
  it("applies the expected default query", () => {
    const parsed = countyListQuerySchema.parse({});

    expect(parsed).toEqual({
      focus: "recruitment",
      age: "all",
      search: "",
      sort: "priority",
      direction: "desc",
    });
  });

  it("trims a county search value", () => {
    const parsed = countyListQuerySchema.parse({
      search: "  Cook  ",
    });

    expect(parsed.search).toBe("Cook");
  });

  it("rejects unsupported query values", () => {
    expect(() =>
      countyListQuerySchema.parse({
        focus: "retention",
      }),
    ).toThrow();

    expect(() =>
      countyListQuerySchema.parse({
        age: "18-21",
      }),
    ).toThrow();

    expect(() =>
      countyListQuerySchema.parse({
        unknownParameter: "value",
      }),
    ).toThrow();
  });
});

describe("county route parameter schema", () => {
  it("accepts a stable county slug", () => {
    expect(
      countyRouteParamsSchema.parse({
        countySlug: "du-page",
      }),
    ).toEqual({
      countySlug: "du-page",
    });
  });

  it("rejects unsafe county route values", () => {
    expect(() =>
      countyRouteParamsSchema.parse({
        countySlug: "../database",
      }),
    ).toThrow();
  });
});

describe("county aggregate schemas", () => {
  it("accepts a valid county summary", () => {
    expect(countySummarySchema.parse(countyFixture)).toEqual(countyFixture);
  });

  it("accepts meaningful null metrics", () => {
    const parsed = countySummarySchema.parse({
      ...countyFixture,
      childrenPerCurrentHome: null,
      localPlacementRate: null,
      medianObservedActiveDayRate: null,
    });

    expect(parsed.childrenPerCurrentHome).toBeNull();
    expect(parsed.localPlacementRate).toBeNull();
    expect(parsed.medianObservedActiveDayRate).toBeNull();
  });

  it("rejects rates outside zero and one", () => {
    expect(() =>
      countySummarySchema.parse({
        ...countyFixture,
        localPlacementRate: 1.1,
      }),
    ).toThrow();
  });

  it("requires the reason count to equal the signal count", () => {
    expect(() =>
      countySummarySchema.parse({
        ...countyFixture,
        recruitment: {
          ...opportunityFixture,
          signalCount: 2,
        },
      }),
    ).toThrow();
  });
});

describe("placement-setting contract", () => {
  it("accepts reconciled placement-setting counts", () => {
    const parsed = countyPlacementSettingsSchema.parse({
      totalCurrentPlacements: 120,
      kin: {
        count: 58,
        share: 58 / 120,
      },
      fosterHome: {
        count: 60,
        share: 0.5,
      },
      nonfamily: {
        count: 2,
        share: 2 / 120,
      },
    });

    expect(parsed.totalCurrentPlacements).toBe(120);
  });

  it("rejects placement-setting counts that do not reconcile", () => {
    expect(() =>
      countyPlacementSettingsSchema.parse({
        totalCurrentPlacements: 120,
        kin: {
          count: 50,
          share: 50 / 120,
        },
        fosterHome: {
          count: 60,
          share: 0.5,
        },
        nonfamily: {
          count: 2,
          share: 2 / 120,
        },
      }),
    ).toThrow();
  });
});

describe("API response contracts", () => {
  it("accepts a county-list response", () => {
    const parsed = countyListResponseSchema.parse({
      metadata: metadataFixture,
      query: {},
      statewide: statewideFixture,
      counties: [countyFixture],
      totalCount: 1,
    });

    expect(parsed.query.focus).toBe("recruitment");
    expect(parsed.totalCount).toBe(1);
  });

  it("rejects an incorrect county-list total", () => {
    expect(() =>
      countyListResponseSchema.parse({
        metadata: metadataFixture,
        query: {},
        statewide: statewideFixture,
        counties: [countyFixture],
        totalCount: 2,
      }),
    ).toThrow();
  });

  it("accepts a complete county-detail response", () => {
    const parsed = countyDetailResponseSchema.parse({
      metadata: metadataFixture,
      diagnosis:
        "Additional recruitment may be the stronger area to investigate.",
      county: countyFixture,
      placementSettings: {
        totalCurrentPlacements: 120,
        kin: {
          count: 58,
          share: 58 / 120,
        },
        fosterHome: {
          count: 60,
          share: 0.5,
        },
        nonfamily: {
          count: 2,
          share: 2 / 120,
        },
      },
      ageAlignment: [
        {
          ageBand: "0-5",
          currentChildren: 35,
          preferenceMatchingHomes: 12,
          childrenPerMatchingHome: 35 / 12,
          limitedData: false,
          recruitmentEvidence: false,
          statewideP75Threshold: 4.2,
        },
        {
          ageBand: "6-12",
          currentChildren: 40,
          preferenceMatchingHomes: 11,
          childrenPerMatchingHome: 40 / 11,
          limitedData: false,
          recruitmentEvidence: false,
          statewideP75Threshold: 4.5,
        },
        {
          ageBand: "13-17",
          currentChildren: 45,
          preferenceMatchingHomes: 8,
          childrenPerMatchingHome: 45 / 8,
          limitedData: false,
          recruitmentEvidence: true,
          statewideP75Threshold: 5.1,
        },
      ],
      placementFlows: [
        {
          destinationCountyName: "Example",
          placementCount: 20,
          placementShare: 1 / 3,
          isLocal: true,
        },
        {
          destinationCountyName: "Neighbor",
          placementCount: 40,
          placementShare: 2 / 3,
          isLocal: false,
        },
      ],
      investigationQuestions: [
        {
          displayOrder: 1,
          questionText: "What factors affect local placement options?",
        },
        {
          displayOrder: 2,
          questionText:
            "Which age groups need additional recruitment attention?",
        },
        {
          displayOrder: 3,
          questionText:
            "What cross-county coordination should staff investigate?",
        },
      ],
      capacityTrend: [
        {
          snapshotDate: "2025-07-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2025-08-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2025-09-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2025-10-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2025-11-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2025-12-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2026-01-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2026-02-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2026-03-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2026-04-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2026-05-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2026-06-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
        {
          snapshotDate: "2026-07-01",
          childrenCurrentlyInCare: 10,
          currentFosterHomes: 2,
          childrenPerCurrentHome: 5,
        },
      ],
      capacityTrendSummary: {
        twelveMonthsAgoRatio: 5,
        currentRatio: 5,
        absoluteChange: 0,
        percentChange: 0,
        direction: "stable",
      },
    });

    expect(parsed.county.countySlug).toBe("example");
  });

  it("accepts a health response", () => {
    const parsed = healthResponseSchema.parse({
      status: "ok",
      service: "foster-home-capacity-explorer",
      schemaVersion: "1.1",
      dataCutoff: "2026-07-01",
      observationStart: "2022-01-01",
      buildStatus: "complete",
      appVersion: "0.1.0",
      commitSha: null,
    });

    expect(parsed.status).toBe("ok");
  });

  it("accepts a stable API error envelope", () => {
    const parsed = apiErrorResponseSchema.parse({
      error: {
        code: "COUNTY_NOT_FOUND",
        message: "The requested county was not found.",
      },
      requestId: "request-123",
    });

    expect(parsed.error.code).toBe("COUNTY_NOT_FOUND");
  });
});
