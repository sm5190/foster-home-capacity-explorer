import { afterAll, describe, expect, it } from "vitest";

import { closeDatabaseConnection } from "../../lib/db";
import {
  SqliteCountyRepository,
  SqliteStatewideRepository,
} from "../../lib/repositories";

const statewideRepository = new SqliteStatewideRepository();

const countyRepository = new SqliteCountyRepository();

describe("typed SQLite repositories", () => {
  afterAll(() => {
    closeDatabaseConnection();
  });

  it("reads the statewide summary", () => {
    const summary = statewideRepository.getSummary();

    expect(summary).toEqual({
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
      renewalsWithin90Days: 1457,
      renewalsWithoutRecentActivity: 184,

      localFosterPlacements: 1_519,
      outOfCountyFosterPlacements: 2_824,
      localPlacementRate: expect.closeTo(1_519 / 4_343, 8),

      medianObservedActiveDayRate: expect.any(Number),
    });
  });

  it("returns all county summaries", () => {
    const counties = countyRepository.listSummaries();

    expect(counties).toHaveLength(103);

    const uniqueSlugs = new Set(counties.map((county) => county.countySlug));

    expect(uniqueSlugs.size).toBe(103);
    expect(counties.some((county) => county.countySlug === "cook")).toBe(true);
  });

  it("reads a county summary by slug", () => {
    const cook = countyRepository.findSummaryBySlug("cook");

    expect(cook).not.toBeNull();

    expect(cook).toMatchObject({
      countySlug: "cook",
      countyName: "Cook",

      childrenCurrentlyInCare: 1_933,

      currentKinPlacements: 879,
      currentFosterPlacements: 1_044,
      currentNonfamilyPlacements: 10,

      limitedData: expect.any(Boolean),
    });

    expect(
      cook!.currentKinPlacements +
        cook!.currentFosterPlacements +
        cook!.currentNonfamilyPlacements,
    ).toBe(cook!.childrenCurrentlyInCare);

    expect(
      cook!.localFosterPlacements + cook!.outOfCountyFosterPlacements,
    ).toBe(cook!.currentFosterPlacements);
  });

  it("reads all stored county signals in one query", () => {
    const counties = countyRepository.listSummaries();

    const signals = countyRepository.listSignals();

    const expectedSignalCount = counties.reduce(
      (total, county) =>
        total + county.recruitmentSignalCount + county.engagementSignalCount,
      0,
    );

    expect(signals).toHaveLength(expectedSignalCount);
  });

  it("returns null for an unknown valid county slug", () => {
    expect(countyRepository.findSummaryBySlug("not-a-real-county")).toBeNull();
  });

  it("reads county signals that reconcile to signal counts", () => {
    const cook = countyRepository.findSummaryBySlug("cook");

    expect(cook).not.toBeNull();

    const signals = countyRepository.listSignalsForCounty("cook");

    const recruitmentSignals = signals.filter(
      (signal) => signal.focus === "recruitment",
    );

    const engagementSignals = signals.filter(
      (signal) => signal.focus === "engagement",
    );

    expect(recruitmentSignals).toHaveLength(cook!.recruitmentSignalCount);

    expect(engagementSignals).toHaveLength(cook!.engagementSignalCount);

    for (const signal of signals) {
      expect(signal.countySlug).toBe("cook");
      expect(["recruitment", "engagement"]).toContain(signal.focus);
    }
  });

  it("reads one age band for all counties", () => {
    const rows = countyRepository.listAgeAlignmentForBand("0-5");

    expect(rows).toHaveLength(103);

    for (const row of rows) {
      expect(row.ageBand).toBe("0-5");
    }
  });

  it("reads ordered age-alignment rows", () => {
    const ageAlignment = countyRepository.listAgeAlignmentForCounty("cook");

    expect(ageAlignment.length).toBeGreaterThanOrEqual(3);
    expect(ageAlignment.length).toBeLessThanOrEqual(4);

    const ageBands = ageAlignment.map((row) => row.ageBand);

    expect(ageBands).toContain("0-5");
    expect(ageBands).toContain("6-12");
    expect(ageBands).toContain("13-17");

    for (const row of ageAlignment) {
      expect(row.countySlug).toBe("cook");
      expect(typeof row.limitedData).toBe("boolean");
      expect(typeof row.recruitmentEvidence).toBe("boolean");
    }
  });

  it("reads placement flows that reconcile to foster placements", () => {
    const cook = countyRepository.findSummaryBySlug("cook");

    expect(cook).not.toBeNull();

    const flows = countyRepository.listPlacementFlowsForCounty("cook");

    const placementCount = flows.reduce(
      (total, flow) => total + flow.placementCount,
      0,
    );

    const placementShare = flows.reduce(
      (total, flow) => total + flow.placementShare,
      0,
    );

    expect(placementCount).toBe(cook!.currentFosterPlacements);

    expect(placementShare).toBeCloseTo(1, 8);

    const localFlow = flows.find((flow) => flow.isLocal);

    expect(localFlow).toBeDefined();
    expect(localFlow!.placementCount).toBe(cook!.localFosterPlacements);
  });

  it("reads ordered investigation questions", () => {
    const questions =
      countyRepository.listInvestigationQuestionsForCounty("cook");

    expect(questions.length).toBeGreaterThanOrEqual(3);

    expect(questions.length).toBeLessThanOrEqual(5);

    expect(questions.map((question) => question.displayOrder)).toEqual(
      questions.map((_, index) => index + 1),
    );

    for (const question of questions) {
      expect(question.countySlug).toBe("cook");
      expect(question.questionText.trim().length).toBeGreaterThan(0);
    }
  });

  it("returns empty detail collections for an unknown county", () => {
    const countySlug = "not-a-real-county";

    expect(countyRepository.listSignalsForCounty(countySlug)).toEqual([]);

    expect(countyRepository.listAgeAlignmentForCounty(countySlug)).toEqual([]);

    expect(countyRepository.listPlacementFlowsForCounty(countySlug)).toEqual(
      [],
    );

    expect(
      countyRepository.listInvestigationQuestionsForCounty(countySlug),
    ).toEqual([]);
  });
});
