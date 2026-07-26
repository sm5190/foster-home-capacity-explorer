import { describe, expect, it } from "vitest";

import illinoisCountyData from "../../lib/map/illinois-counties.json";

describe("Illinois priority map data", () => {
  it("contains exactly 102 Illinois counties", () => {
    expect(illinoisCountyData.features).toHaveLength(102);
  });

  it("contains unique county slugs and FIPS codes", () => {
    const countySlugs = illinoisCountyData.features.map(
      (county) => county.properties.countySlug,
    );

    const fipsCodes = illinoisCountyData.features.map(
      (county) => county.properties.fips,
    );

    expect(new Set(countySlugs).size).toBe(102);

    expect(new Set(fipsCodes).size).toBe(102);

    expect(fipsCodes.every((fips) => fips.startsWith("17"))).toBe(true);
  });

  it("uses canonical Vermilion spelling", () => {
    const countySlugs = illinoisCountyData.features.map(
      (county) => county.properties.countySlug,
    );

    expect(countySlugs).toContain("vermilion");

    expect(countySlugs).not.toContain("vermillion");
  });

  it("contains key Illinois counties", () => {
    const countySlugs = illinoisCountyData.features.map(
      (county) => county.properties.countySlug,
    );

    expect(countySlugs).toContain("cook");
    expect(countySlugs).toContain("champaign");
    expect(countySlugs).toContain("rock-island");
    expect(countySlugs).toContain("st-clair");
  });
});
