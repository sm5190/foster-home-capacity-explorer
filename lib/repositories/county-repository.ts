import "server-only";

import { getDatabase } from "../db";
import {
  countySlugSchema,
  detailAgeBandSchema,
  focusSchema,
  opportunityLevelSchema,
  opportunityReasonCodeSchema,
  primaryOpportunitySchema,
} from "../schemas";
import { RepositoryDataError } from "./errors";
import type {
  CountyAgeAlignmentRecord,
  CountyInvestigationQuestionRecord,
  CountyPlacementFlowRecord,
  CountySignalRecord,
  CountySummaryRecord,
} from "./types";

type DatabaseConnection = ReturnType<typeof getDatabase>;

type CountySummaryRow = {
  county_slug: string;
  county_name: string;

  children_currently_in_care: number;

  current_kin_placements: number;
  current_foster_placements: number;
  current_nonfamily_placements: number;

  current_foster_homes: number;
  children_per_current_home: number | null;

  local_foster_placements: number;
  out_of_county_foster_placements: number;
  local_placement_rate: number | null;

  homes_with_current_placement: number;
  homes_with_recent_activity: number;
  homes_without_recent_activity: number;
  median_observed_active_day_rate: number | null;
  renewals_within_90_days: number;

  recruitment_level: string;
  recruitment_signal_count: number;

  engagement_level: string;
  engagement_signal_count: number;

  primary_opportunity: string;
  limited_data: number;
};

type CountySignalRow = {
  county_slug: string;
  focus: string;
  signal_code: string;
  signal_value: number | null;
  threshold_value: number | null;
};

type CountyAgeAlignmentRow = {
  county_slug: string;
  age_band: string;
  current_children: number;
  preference_matching_homes: number;
  children_per_matching_home: number | null;
  limited_data: number;
  recruitment_evidence: number;
  statewide_p75_threshold: number | null;
};

type CountyPlacementFlowRow = {
  origin_county_slug: string;
  destination_county_name: string;
  placement_count: number;
  placement_share: number;
  is_local: number;
};

type CountyInvestigationQuestionRow = {
  county_slug: string;
  display_order: number;
  question_text: string;
};

export interface CountyRepository {
  listSummaries(): readonly CountySummaryRecord[];

  findSummaryBySlug(countySlug: string): CountySummaryRecord | null;

  listSignalsForCounty(countySlug: string): readonly CountySignalRecord[];

  listAgeAlignmentForCounty(
    countySlug: string,
  ): readonly CountyAgeAlignmentRecord[];

  listPlacementFlowsForCounty(
    countySlug: string,
  ): readonly CountyPlacementFlowRecord[];

  listInvestigationQuestionsForCounty(
    countySlug: string,
  ): readonly CountyInvestigationQuestionRecord[];
}

function parseSqliteBoolean(value: number, fieldName: string): boolean {
  if (value === 0) {
    return false;
  }

  if (value === 1) {
    return true;
  }

  throw new RepositoryDataError(
    `Expected ${fieldName} to contain 0 or 1, received ${value}.`,
  );
}

function mapCountySummary(row: CountySummaryRow): CountySummaryRecord {
  return {
    countySlug: row.county_slug,
    countyName: row.county_name,

    childrenCurrentlyInCare: row.children_currently_in_care,

    currentKinPlacements: row.current_kin_placements,
    currentFosterPlacements: row.current_foster_placements,
    currentNonfamilyPlacements: row.current_nonfamily_placements,

    currentFosterHomes: row.current_foster_homes,
    childrenPerCurrentHome: row.children_per_current_home,

    localFosterPlacements: row.local_foster_placements,
    outOfCountyFosterPlacements: row.out_of_county_foster_placements,
    localPlacementRate: row.local_placement_rate,

    homesWithCurrentPlacement: row.homes_with_current_placement,
    homesWithRecentActivity: row.homes_with_recent_activity,
    homesWithoutRecentActivity: row.homes_without_recent_activity,
    medianObservedActiveDayRate: row.median_observed_active_day_rate,
    renewalsWithin90Days: row.renewals_within_90_days,

    recruitmentLevel: opportunityLevelSchema.parse(row.recruitment_level),
    recruitmentSignalCount: row.recruitment_signal_count,

    engagementLevel: opportunityLevelSchema.parse(row.engagement_level),
    engagementSignalCount: row.engagement_signal_count,

    primaryOpportunity: primaryOpportunitySchema.parse(row.primary_opportunity),
    limitedData: parseSqliteBoolean(
      row.limited_data,
      "county_summary.limited_data",
    ),
  };
}

export class SqliteCountyRepository implements CountyRepository {
  constructor(private readonly database: DatabaseConnection = getDatabase()) {}

  listSummaries(): readonly CountySummaryRecord[] {
    const rows = this.database
      .prepare(
        `
          SELECT
            county_slug,
            county_name,
            children_currently_in_care,
            current_kin_placements,
            current_foster_placements,
            current_nonfamily_placements,
            current_foster_homes,
            children_per_current_home,
            local_foster_placements,
            out_of_county_foster_placements,
            local_placement_rate,
            homes_with_current_placement,
            homes_with_recent_activity,
            homes_without_recent_activity,
            median_observed_active_day_rate,
            renewals_within_90_days,
            recruitment_level,
            recruitment_signal_count,
            engagement_level,
            engagement_signal_count,
            primary_opportunity,
            limited_data
          FROM county_summary
          ORDER BY
            county_name COLLATE NOCASE ASC,
            county_slug ASC
        `,
      )
      .all() as CountySummaryRow[];

    return rows.map(mapCountySummary);
  }

  findSummaryBySlug(countySlug: string): CountySummaryRecord | null {
    const parsedSlug = countySlugSchema.parse(countySlug);

    const row = this.database
      .prepare(
        `
          SELECT
            county_slug,
            county_name,
            children_currently_in_care,
            current_kin_placements,
            current_foster_placements,
            current_nonfamily_placements,
            current_foster_homes,
            children_per_current_home,
            local_foster_placements,
            out_of_county_foster_placements,
            local_placement_rate,
            homes_with_current_placement,
            homes_with_recent_activity,
            homes_without_recent_activity,
            median_observed_active_day_rate,
            renewals_within_90_days,
            recruitment_level,
            recruitment_signal_count,
            engagement_level,
            engagement_signal_count,
            primary_opportunity,
            limited_data
          FROM county_summary
          WHERE county_slug = ?
        `,
      )
      .get(parsedSlug) as CountySummaryRow | undefined;

    return row ? mapCountySummary(row) : null;
  }

  listSignalsForCounty(countySlug: string): readonly CountySignalRecord[] {
    const parsedSlug = countySlugSchema.parse(countySlug);

    const rows = this.database
      .prepare(
        `
          SELECT
            county_slug,
            focus,
            signal_code,
            signal_value,
            threshold_value
          FROM county_signal
          WHERE county_slug = ?
          ORDER BY
            focus ASC,
            signal_code ASC
        `,
      )
      .all(parsedSlug) as CountySignalRow[];

    return rows.map((row) => ({
      countySlug: row.county_slug,
      focus: focusSchema.parse(row.focus),
      signalCode: opportunityReasonCodeSchema.parse(row.signal_code),
      signalValue: row.signal_value,
      thresholdValue: row.threshold_value,
    }));
  }

  listAgeAlignmentForCounty(
    countySlug: string,
  ): readonly CountyAgeAlignmentRecord[] {
    const parsedSlug = countySlugSchema.parse(countySlug);

    const rows = this.database
      .prepare(
        `
          SELECT
            county_slug,
            age_band,
            current_children,
            preference_matching_homes,
            children_per_matching_home,
            limited_data,
            recruitment_evidence,
            statewide_p75_threshold
          FROM county_age_alignment
          WHERE county_slug = ?
          ORDER BY
            CASE age_band
              WHEN '0-5' THEN 1
              WHEN '6-12' THEN 2
              WHEN '13-17' THEN 3
              WHEN 'unknown' THEN 4
              ELSE 5
            END
        `,
      )
      .all(parsedSlug) as CountyAgeAlignmentRow[];

    return rows.map((row) => ({
      countySlug: row.county_slug,
      ageBand: detailAgeBandSchema.parse(row.age_band),
      currentChildren: row.current_children,
      preferenceMatchingHomes: row.preference_matching_homes,
      childrenPerMatchingHome: row.children_per_matching_home,
      limitedData: parseSqliteBoolean(
        row.limited_data,
        "county_age_alignment.limited_data",
      ),
      recruitmentEvidence: parseSqliteBoolean(
        row.recruitment_evidence,
        "county_age_alignment.recruitment_evidence",
      ),
      statewideP75Threshold: row.statewide_p75_threshold,
    }));
  }

  listPlacementFlowsForCounty(
    countySlug: string,
  ): readonly CountyPlacementFlowRecord[] {
    const parsedSlug = countySlugSchema.parse(countySlug);

    const rows = this.database
      .prepare(
        `
          SELECT
            origin_county_slug,
            destination_county_name,
            placement_count,
            placement_share,
            is_local
          FROM county_placement_flow
          WHERE origin_county_slug = ?
          ORDER BY
            placement_count DESC,
            destination_county_name COLLATE NOCASE ASC
        `,
      )
      .all(parsedSlug) as CountyPlacementFlowRow[];

    return rows.map((row) => ({
      originCountySlug: row.origin_county_slug,
      destinationCountyName: row.destination_county_name,
      placementCount: row.placement_count,
      placementShare: row.placement_share,
      isLocal: parseSqliteBoolean(
        row.is_local,
        "county_placement_flow.is_local",
      ),
    }));
  }

  listInvestigationQuestionsForCounty(
    countySlug: string,
  ): readonly CountyInvestigationQuestionRecord[] {
    const parsedSlug = countySlugSchema.parse(countySlug);

    const rows = this.database
      .prepare(
        `
          SELECT
            county_slug,
            display_order,
            question_text
          FROM county_investigation_question
          WHERE county_slug = ?
          ORDER BY display_order ASC
        `,
      )
      .all(parsedSlug) as CountyInvestigationQuestionRow[];

    return rows.map((row) => ({
      countySlug: row.county_slug,
      displayOrder: row.display_order,
      questionText: row.question_text,
    }));
  }
}
