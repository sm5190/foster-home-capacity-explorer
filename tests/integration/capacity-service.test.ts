import { afterAll, describe, expect, it } from "vitest";

import { closeDatabaseConnection } from "../../lib/db";
import { SqliteCountyRepository } from "../../lib/repositories";
import { CountyNotFoundError, createCapacityService } from "../../lib/services";

const service = createCapacityService();

const countyRepository = new SqliteCountyRepository();

describe("capacity service", () => {
  afterAll(() => {
    closeDatabaseConnection();
  });

  it("returns the default statewide priority response", () => {
    const response = service.getStatewidePriorities();

    expect(response.metadata).toEqual({
      schemaVersion: "1.3",
      reportingCutoff: "2026-07-01",
      observationStart: "2022-01-01",
      buildStatus: "complete",
    });

    expect(response.query).toEqual({
      focus: "recruitment",
      age: "all",
      search: "",
      sort: "priority",
      direction: "desc",
    });

    expect(response.counties).toHaveLength(102);

    expect(response.totalCount).toBe(102);
  });

  it("filters county priorities by county name", () => {
    const response = service.getStatewidePriorities({
      search: "Cook",
    });

    expect(
      response.counties.some((county) => county.countySlug === "cook"),
    ).toBe(true);

    for (const county of response.counties) {
      expect(county.countyName.toLocaleLowerCase().includes("cook")).toBe(true);
    }
  });

  it("sorts county names in ascending order", () => {
    const response = service.getStatewidePriorities({
      sort: "county",
      direction: "asc",
    });

    const names = response.counties.map((county) => county.countyName);

    expect(names).toEqual(
      [...names].sort((first, second) => first.localeCompare(second)),
    );
  });

  it("applies selected age-group recruitment evidence", () => {
    const ageBands = ["0-5", "6-12", "13-17"] as const;

    const evidenceRow = ageBands
      .flatMap((ageBand) => countyRepository.listAgeAlignmentForBand(ageBand))
      .find((row) => row.recruitmentEvidence);

    expect(evidenceRow).toBeDefined();

    const countyRecord = countyRepository.findSummaryBySlug(
      evidenceRow!.countySlug,
    );

    expect(countyRecord).not.toBeNull();

    const baseResponse = service.getStatewidePriorities({
      search: countyRecord!.countyName,
      age: "all",
    });

    const ageBand = evidenceRow!.ageBand;

    if (ageBand === "unknown") {
      throw new Error("Expected a known age band for recruitment evidence");
    }

    const ageResponse = service.getStatewidePriorities({
      search: countyRecord!.countyName,
      age: ageBand,
    });

    const baseCounty = baseResponse.counties.find(
      (county) => county.countySlug === evidenceRow!.countySlug,
    );

    const ageCounty = ageResponse.counties.find(
      (county) => county.countySlug === evidenceRow!.countySlug,
    );

    expect(baseCounty).toBeDefined();
    expect(ageCounty).toBeDefined();

    expect(ageCounty!.recruitment.signalCount).toBe(
      baseCounty!.recruitment.signalCount + 1,
    );

    expect(
      ageCounty!.recruitment.reasons.some(
        (reason) =>
          reason.code === "high_children_per_preference_matching_home",
      ),
    ).toBe(true);
  });

  it("builds the complete Cook County brief", () => {
    const response = service.getCountyCapacityBrief("cook");

    expect(response.county).toMatchObject({
      countySlug: "cook",
      countyName: "Cook",
      childrenCurrentlyInCare: 1_933,
      currentFosterPlacements: 1_044,
    });

    expect(
      response.placementSettings.kin.count +
        response.placementSettings.fosterHome.count +
        response.placementSettings.nonfamily.count,
    ).toBe(response.placementSettings.totalCurrentPlacements);

    const placementSettingShare =
      response.placementSettings.kin.share! +
      response.placementSettings.fosterHome.share! +
      response.placementSettings.nonfamily.share!;

    expect(placementSettingShare).toBeCloseTo(1, 8);

    const placementFlowCount = response.placementFlows.reduce(
      (total, flow) => total + flow.placementCount,
      0,
    );

    expect(placementFlowCount).toBe(response.county.currentFosterPlacements);

    expect(response.investigationQuestions.length).toBeGreaterThanOrEqual(3);

    expect(response.investigationQuestions.length).toBeLessThanOrEqual(5);

    expect(response.diagnosis.length).toBeGreaterThan(0);
  });

  it("throws a typed error for an unknown county", () => {
    expect(() => service.getCountyCapacityBrief("not-a-real-county")).toThrow(
      CountyNotFoundError,
    );
  });
});
