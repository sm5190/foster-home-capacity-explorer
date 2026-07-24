import "server-only";

import { getDatabase } from "../db";
import { RepositoryDataError } from "./errors";
import type { StatewideSummaryRecord } from "./types";

type DatabaseConnection = ReturnType<typeof getDatabase>;

type StatewideSummaryRow = {
  reporting_cutoff: string;
  observation_start: string;

  children_currently_in_care: number;

  current_kin_placements: number;
  current_foster_home_placements: number;
  current_nonfamily_placements: number;

  current_foster_homes: number;
  homes_with_current_placement: number;
  homes_with_recent_activity: number;
  homes_without_recent_activity: number;

  local_foster_placements: number;
  out_of_county_foster_placements: number;
  local_placement_rate: number | null;

  median_observed_active_day_rate: number | null;
};

export interface StatewideRepository {
  getSummary(): StatewideSummaryRecord;
}

function mapStatewideSummary(row: StatewideSummaryRow): StatewideSummaryRecord {
  return {
    reportingCutoff: row.reporting_cutoff,
    observationStart: row.observation_start,

    childrenCurrentlyInCare: row.children_currently_in_care,

    currentKinPlacements: row.current_kin_placements,
    currentFosterHomePlacements: row.current_foster_home_placements,
    currentNonfamilyPlacements: row.current_nonfamily_placements,

    currentFosterHomes: row.current_foster_homes,
    homesWithCurrentPlacement: row.homes_with_current_placement,
    homesWithRecentActivity: row.homes_with_recent_activity,
    homesWithoutRecentActivity: row.homes_without_recent_activity,

    localFosterPlacements: row.local_foster_placements,
    outOfCountyFosterPlacements: row.out_of_county_foster_placements,
    localPlacementRate: row.local_placement_rate,

    medianObservedActiveDayRate: row.median_observed_active_day_rate,
  };
}

export class SqliteStatewideRepository implements StatewideRepository {
  constructor(private readonly database: DatabaseConnection = getDatabase()) {}

  getSummary(): StatewideSummaryRecord {
    const row = this.database
      .prepare(
        `
          SELECT
            reporting_cutoff,
            observation_start,
            children_currently_in_care,
            current_kin_placements,
            current_foster_home_placements,
            current_nonfamily_placements,
            current_foster_homes,
            homes_with_current_placement,
            homes_with_recent_activity,
            homes_without_recent_activity,
            local_foster_placements,
            out_of_county_foster_placements,
            local_placement_rate,
            median_observed_active_day_rate
          FROM statewide_summary
          WHERE id = 1
        `,
      )
      .get() as StatewideSummaryRow | undefined;

    if (!row) {
      throw new RepositoryDataError(
        "The statewide aggregate summary is missing.",
      );
    }

    return mapStatewideSummary(row);
  }
}
