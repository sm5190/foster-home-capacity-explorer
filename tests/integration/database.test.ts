import { existsSync } from "node:fs";

import { afterAll, describe, expect, it } from "vitest";

import {
  closeDatabaseConnection,
  getDatabase,
  getDatabaseMetadata,
  getDatabasePath,
} from "../../lib/db";

type StatewideSummaryRow = {
  children_currently_in_care: number;
  current_foster_homes: number;
  local_foster_placements: number;
  out_of_county_foster_placements: number;
};

type CountRow = {
  row_count: number;
};

type CountyPlacementSettingsRow = {
  children_currently_in_care: number;
  current_kin_placements: number;
  current_foster_placements: number;
  current_nonfamily_placements: number;
};

describe("runtime SQLite database", () => {
  afterAll(() => {
    closeDatabaseConnection();
  });

  it("resolves an existing aggregate database file", () => {
    const databasePath = getDatabasePath();

    expect(existsSync(databasePath)).toBe(true);
    expect(databasePath.endsWith("foster_capacity.db")).toBe(true);
  });

  it("opens one shared read-only connection", () => {
    const firstConnection = getDatabase();
    const secondConnection = getDatabase();

    expect(firstConnection).toBe(secondConnection);
    expect(firstConnection.open).toBe(true);
    expect(firstConnection.readonly).toBe(true);
  });

  it("validates required build metadata", () => {
    const metadata = getDatabaseMetadata();

    expect(metadata).toEqual({
      schemaVersion: "1.3",
      reportingCutoff: "2026-07-01",
      observationStart: "2022-01-01",
      buildStatus: "complete",
    });
  });

  it("reads the validated statewide aggregate", () => {
    const database = getDatabase();

    const statewideSummary = database
      .prepare(
        `
          SELECT
            children_currently_in_care,
            current_foster_homes,
            local_foster_placements,
            out_of_county_foster_placements
          FROM statewide_summary
          WHERE id = 1
        `,
      )
      .get() as StatewideSummaryRow | undefined;

    expect(statewideSummary).toEqual({
      children_currently_in_care: 8_071,
      current_foster_homes: 3_395,
      local_foster_placements: 1_519,
      out_of_county_foster_placements: 2_824,
    });
  });

  it("contains all 103 county summary rows", () => {
    const database = getDatabase();

    const result = database
      .prepare(
        `
          SELECT COUNT(*) AS row_count
          FROM county_summary
        `,
      )
      .get() as CountRow | undefined;

    expect(result?.row_count).toBe(103);
  });

  it("reads county placement-setting aggregates", () => {
    const database = getDatabase();

    const cook = database
      .prepare(
        `
        SELECT
          children_currently_in_care,
          current_kin_placements,
          current_foster_placements,
          current_nonfamily_placements
        FROM county_summary
        WHERE county_slug = ?
      `,
      )
      .get("cook") as CountyPlacementSettingsRow | undefined;

    expect(cook).toEqual({
      children_currently_in_care: 1_933,
      current_kin_placements: 879,
      current_foster_placements: 1_044,
      current_nonfamily_placements: 10,
    });
  });

  it("rejects write operations", () => {
    const database = getDatabase();

    expect(() => {
      database.exec("CREATE TABLE forbidden_runtime_write (id INTEGER);");
    }).toThrow();
  });
});
