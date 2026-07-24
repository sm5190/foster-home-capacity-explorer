import "server-only";

import { getDatabaseMetadata, type RuntimeDatabaseMetadata } from "../db";
import { buildCountyDiagnosis, getOpportunityReasonLabel } from "../narratives";
import {
  SqliteCountyRepository,
  SqliteStatewideRepository,
  type CountyAgeAlignmentRecord,
  type CountyRepository,
  type CountySignalRecord,
  type CountySummaryRecord,
  type StatewideRepository,
} from "../repositories";
import { RepositoryDataError } from "../repositories/errors";
import {
  countyAgeAlignmentSchema,
  countyDetailResponseSchema,
  countyListQuerySchema,
  countyListResponseSchema,
  countyPlacementFlowSchema,
  countyPlacementSettingsSchema,
  countySlugSchema,
  countySummarySchema,
  investigationQuestionSchema,
  opportunityReasonSchema,
  opportunitySummarySchema,
  publicMetadataSchema,
  statewideSummarySchema,
  type AgeFilter,
  type CountyDetailResponse,
  type CountyListQuery,
  type CountyListQueryInput,
  type CountyListResponse,
  type CountySort,
  type CountySummary,
  type OpportunityLevel,
  type OpportunityReason,
  type OpportunitySummary,
  type PrimaryOpportunity,
  type PublicMetadata,
  type SortDirection,
} from "../schemas";
import { CountyNotFoundError } from "./errors";

type MetadataProvider = () => RuntimeDatabaseMetadata;

function toPublicMetadata(metadata: RuntimeDatabaseMetadata): PublicMetadata {
  return publicMetadataSchema.parse({
    schemaVersion: metadata.schemaVersion,
    reportingCutoff: metadata.reportingCutoff,
    observationStart: metadata.observationStart,
    buildStatus: metadata.buildStatus,
  });
}

function classifyOpportunity(
  signalCount: number,
  limitedData: boolean,
): OpportunityLevel {
  if (limitedData) {
    return "limited";
  }

  if (signalCount >= 2) {
    return "higher";
  }

  if (signalCount === 1) {
    return "possible";
  }

  return "review";
}

function determinePrimaryOpportunity(
  recruitment: OpportunitySummary,
  engagement: OpportunitySummary,
): PrimaryOpportunity {
  const recruitmentLimited = recruitment.level === "limited";

  const engagementLimited = engagement.level === "limited";

  if (recruitmentLimited && engagementLimited) {
    return "review";
  }

  if (recruitmentLimited) {
    return engagement.signalCount > 0 ? "engagement" : "review";
  }

  if (engagementLimited) {
    return recruitment.signalCount > 0 ? "recruitment" : "review";
  }

  if (recruitment.signalCount > engagement.signalCount) {
    return "recruitment";
  }

  if (engagement.signalCount > recruitment.signalCount) {
    return "engagement";
  }

  if (recruitment.signalCount > 0) {
    return "both";
  }

  return "review";
}

function mapSignalReason(signal: CountySignalRecord): OpportunityReason {
  return opportunityReasonSchema.parse({
    code: signal.signalCode,
    label: getOpportunityReasonLabel(signal.signalCode),
    value: signal.signalValue,
    threshold: signal.thresholdValue,
  });
}

function buildBaseOpportunitySummary(
  level: OpportunityLevel,
  signalCount: number,
  signals: readonly CountySignalRecord[],
): OpportunitySummary {
  const reasons = signals.map(mapSignalReason);

  return opportunitySummarySchema.parse({
    level,
    signalCount,
    reasons,
  });
}

function addSelectedAgeEvidence(
  baseSummary: OpportunitySummary,
  ageAlignment: CountyAgeAlignmentRecord,
): OpportunitySummary {
  const signalCount =
    baseSummary.signalCount + (ageAlignment.recruitmentEvidence ? 1 : 0);

  const reasons = [...baseSummary.reasons];

  if (ageAlignment.recruitmentEvidence) {
    reasons.push(
      opportunityReasonSchema.parse({
        code: "high_children_per_preference_matching_home",
        label: getOpportunityReasonLabel(
          "high_children_per_preference_matching_home",
          ageAlignment.ageBand,
        ),
        value: ageAlignment.childrenPerMatchingHome,
        threshold: ageAlignment.statewideP75Threshold,
      }),
    );
  }

  const limitedData =
    baseSummary.level === "limited" || ageAlignment.limitedData;

  return opportunitySummarySchema.parse({
    level: classifyOpportunity(signalCount, limitedData),
    signalCount,
    reasons,
  });
}

function groupSignalsByCounty(
  signals: readonly CountySignalRecord[],
): ReadonlyMap<string, readonly CountySignalRecord[]> {
  const grouped = new Map<string, CountySignalRecord[]>();

  for (const signal of signals) {
    const countySignals = grouped.get(signal.countySlug) ?? [];

    countySignals.push(signal);
    grouped.set(signal.countySlug, countySignals);
  }

  return grouped;
}

function mapAgeAlignmentByCounty(
  rows: readonly CountyAgeAlignmentRecord[],
): ReadonlyMap<string, CountyAgeAlignmentRecord> {
  return new Map(rows.map((row) => [row.countySlug, row]));
}

function buildCountySummary(
  record: CountySummaryRecord,
  signals: readonly CountySignalRecord[],
  selectedAgeAlignment?: CountyAgeAlignmentRecord,
): CountySummary {
  const recruitmentSignals = signals.filter(
    (signal) => signal.focus === "recruitment",
  );

  const engagementSignals = signals.filter(
    (signal) => signal.focus === "engagement",
  );

  const baseRecruitment = buildBaseOpportunitySummary(
    record.recruitmentLevel,
    record.recruitmentSignalCount,
    recruitmentSignals,
  );

  const recruitment = selectedAgeAlignment
    ? addSelectedAgeEvidence(baseRecruitment, selectedAgeAlignment)
    : baseRecruitment;

  const engagement = buildBaseOpportunitySummary(
    record.engagementLevel,
    record.engagementSignalCount,
    engagementSignals,
  );

  const primaryOpportunity = selectedAgeAlignment
    ? determinePrimaryOpportunity(recruitment, engagement)
    : record.primaryOpportunity;

  const limitedData =
    record.limitedData ||
    recruitment.level === "limited" ||
    engagement.level === "limited";

  return countySummarySchema.parse({
    countySlug: record.countySlug,
    countyName: record.countyName,

    childrenCurrentlyInCare: record.childrenCurrentlyInCare,
    currentFosterHomes: record.currentFosterHomes,
    childrenPerCurrentHome: record.childrenPerCurrentHome,

    currentFosterPlacements: record.currentFosterPlacements,
    localFosterPlacements: record.localFosterPlacements,
    outOfCountyFosterPlacements: record.outOfCountyFosterPlacements,
    localPlacementRate: record.localPlacementRate,

    homesWithCurrentPlacement: record.homesWithCurrentPlacement,
    homesWithRecentActivity: record.homesWithRecentActivity,
    homesWithoutRecentActivity: record.homesWithoutRecentActivity,
    medianObservedActiveDayRate: record.medianObservedActiveDayRate,
    renewalsWithin90Days: record.renewalsWithin90Days,

    recruitment,
    engagement,

    primaryOpportunity,
    limitedData,
  });
}

function compareNullableNumbers(
  first: number | null,
  second: number | null,
  direction: SortDirection,
): number {
  if (first === null && second === null) {
    return 0;
  }

  if (first === null) {
    return 1;
  }

  if (second === null) {
    return -1;
  }

  const difference = first - second;

  return direction === "asc" ? difference : -difference;
}

function getNumericSortValue(
  county: CountySummary,
  sort: CountySort,
): number | null {
  switch (sort) {
    case "childrenCurrentlyInCare":
      return county.childrenCurrentlyInCare;

    case "currentFosterHomes":
      return county.currentFosterHomes;

    case "childrenPerCurrentHome":
      return county.childrenPerCurrentHome;

    case "localPlacementRate":
      return county.localPlacementRate;

    case "homesWithoutRecentActivity":
      return county.homesWithoutRecentActivity;

    case "medianObservedActiveDayRate":
      return county.medianObservedActiveDayRate;

    case "renewalsWithin90Days":
      return county.renewalsWithin90Days;

    case "priority":
    case "county":
      return null;
  }
}

function comparePriority(
  first: CountySummary,
  second: CountySummary,
  query: CountyListQuery,
): number {
  const firstOpportunity =
    query.focus === "recruitment" ? first.recruitment : first.engagement;

  const secondOpportunity =
    query.focus === "recruitment" ? second.recruitment : second.engagement;

  const firstLimited = firstOpportunity.level === "limited";

  const secondLimited = secondOpportunity.level === "limited";

  if (firstLimited !== secondLimited) {
    return firstLimited ? 1 : -1;
  }

  if (firstOpportunity.signalCount !== secondOpportunity.signalCount) {
    const difference =
      firstOpportunity.signalCount - secondOpportunity.signalCount;

    return query.direction === "asc" ? difference : -difference;
  }

  return first.countyName.localeCompare(second.countyName);
}

function compareCounties(
  first: CountySummary,
  second: CountySummary,
  query: CountyListQuery,
): number {
  if (query.sort === "priority") {
    return comparePriority(first, second, query);
  }

  if (query.sort === "county") {
    const comparison = first.countyName.localeCompare(second.countyName);

    return query.direction === "asc" ? comparison : -comparison;
  }

  const comparison = compareNullableNumbers(
    getNumericSortValue(first, query.sort),
    getNumericSortValue(second, query.sort),
    query.direction,
  );

  if (comparison !== 0) {
    return comparison;
  }

  return first.countyName.localeCompare(second.countyName);
}

function calculateShare(count: number, denominator: number): number | null {
  if (denominator === 0) {
    return null;
  }

  return count / denominator;
}

export class CapacityService {
  constructor(
    private readonly statewideRepository: StatewideRepository,
    private readonly countyRepository: CountyRepository,
    private readonly metadataProvider: MetadataProvider = getDatabaseMetadata,
  ) {}

  getStatewidePriorities(input: CountyListQueryInput = {}): CountyListResponse {
    const query = countyListQuerySchema.parse(input);

    const metadata = toPublicMetadata(this.metadataProvider());

    const statewide = statewideSummarySchema.parse(
      this.statewideRepository.getSummary(),
    );

    const countyRecords = this.countyRepository.listSummaries();

    const signalsByCounty = groupSignalsByCounty(
      this.countyRepository.listSignals(),
    );

    let ageAlignmentByCounty:
      ReadonlyMap<string, CountyAgeAlignmentRecord> | undefined;

    if (query.age !== "all") {
      ageAlignmentByCounty = mapAgeAlignmentByCounty(
        this.countyRepository.listAgeAlignmentForBand(query.age),
      );
    }

    const counties = countyRecords.map((record) => {
      const signals = signalsByCounty.get(record.countySlug) ?? [];

      const selectedAgeAlignment = ageAlignmentByCounty?.get(record.countySlug);

      if (query.age !== "all" && !selectedAgeAlignment) {
        throw new RepositoryDataError(
          "Missing selected age-alignment row for " +
            `${record.countySlug}: ${query.age}`,
        );
      }

      return buildCountySummary(record, signals, selectedAgeAlignment);
    });

    const normalizedSearch = query.search.toLocaleLowerCase();

    const filteredCounties = counties
      .filter((county) => {
        if (!normalizedSearch) {
          return true;
        }

        return county.countyName.toLocaleLowerCase().includes(normalizedSearch);
      })
      .sort((first, second) => compareCounties(first, second, query));

    return countyListResponseSchema.parse({
      metadata,
      query,
      statewide,
      counties: filteredCounties,
      totalCount: filteredCounties.length,
    });
  }

  getCountyCapacityBrief(rawCountySlug: string): CountyDetailResponse {
    const countySlug = countySlugSchema.parse(rawCountySlug);

    const record = this.countyRepository.findSummaryBySlug(countySlug);

    if (!record) {
      throw new CountyNotFoundError(countySlug);
    }

    const signals = this.countyRepository.listSignalsForCounty(countySlug);

    const county = buildCountySummary(record, signals);

    const totalCurrentPlacements = record.childrenCurrentlyInCare;

    const placementSettings = countyPlacementSettingsSchema.parse({
      totalCurrentPlacements,

      kin: {
        count: record.currentKinPlacements,
        share: calculateShare(
          record.currentKinPlacements,
          totalCurrentPlacements,
        ),
      },

      fosterHome: {
        count: record.currentFosterPlacements,
        share: calculateShare(
          record.currentFosterPlacements,
          totalCurrentPlacements,
        ),
      },

      nonfamily: {
        count: record.currentNonfamilyPlacements,
        share: calculateShare(
          record.currentNonfamilyPlacements,
          totalCurrentPlacements,
        ),
      },
    });

    const ageAlignment = this.countyRepository
      .listAgeAlignmentForCounty(countySlug)
      .map((row) =>
        countyAgeAlignmentSchema.parse({
          ageBand: row.ageBand,
          currentChildren: row.currentChildren,
          preferenceMatchingHomes: row.preferenceMatchingHomes,
          childrenPerMatchingHome: row.childrenPerMatchingHome,
          limitedData: row.limitedData,
          recruitmentEvidence: row.recruitmentEvidence,
          statewideP75Threshold: row.statewideP75Threshold,
        }),
      );

    const placementFlows = this.countyRepository
      .listPlacementFlowsForCounty(countySlug)
      .map((row) =>
        countyPlacementFlowSchema.parse({
          destinationCountyName: row.destinationCountyName,
          placementCount: row.placementCount,
          placementShare: row.placementShare,
          isLocal: row.isLocal,
        }),
      );

    const investigationQuestions = this.countyRepository
      .listInvestigationQuestionsForCounty(countySlug)
      .map((row) =>
        investigationQuestionSchema.parse({
          displayOrder: row.displayOrder,
          questionText: row.questionText,
        }),
      );

    return countyDetailResponseSchema.parse({
      metadata: toPublicMetadata(this.metadataProvider()),
      diagnosis: buildCountyDiagnosis(county),
      county,
      placementSettings,
      ageAlignment,
      placementFlows,
      investigationQuestions,
    });
  }
}

export function createCapacityService(): CapacityService {
  return new CapacityService(
    new SqliteStatewideRepository(),
    new SqliteCountyRepository(),
  );
}
