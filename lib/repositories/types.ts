import type {
  DetailAgeBand,
  Focus,
  OpportunityLevel,
  OpportunityReasonCode,
  PrimaryOpportunity,
} from "../schemas";

export type StatewideSummaryRecord = {
  reportingCutoff: string;
  observationStart: string;

  childrenCurrentlyInCare: number;

  currentKinPlacements: number;
  currentFosterHomePlacements: number;
  currentNonfamilyPlacements: number;

  currentFosterHomes: number;
  homesWithCurrentPlacement: number;
  homesWithRecentActivity: number;
  homesWithoutRecentActivity: number;

  localFosterPlacements: number;
  outOfCountyFosterPlacements: number;
  localPlacementRate: number | null;

  medianObservedActiveDayRate: number | null;
};

export type CountySummaryRecord = {
  countySlug: string;
  countyName: string;

  childrenCurrentlyInCare: number;

  currentKinPlacements: number;
  currentFosterPlacements: number;
  currentNonfamilyPlacements: number;

  currentFosterHomes: number;
  childrenPerCurrentHome: number | null;

  localFosterPlacements: number;
  outOfCountyFosterPlacements: number;
  localPlacementRate: number | null;

  homesWithCurrentPlacement: number;
  homesWithRecentActivity: number;
  homesWithoutRecentActivity: number;
  medianObservedActiveDayRate: number | null;
  renewalsWithin90Days: number;

  recruitmentLevel: OpportunityLevel;
  recruitmentSignalCount: number;

  engagementLevel: OpportunityLevel;
  engagementSignalCount: number;

  primaryOpportunity: PrimaryOpportunity;
  limitedData: boolean;
};

export type CountySignalRecord = {
  countySlug: string;
  focus: Focus;
  signalCode: OpportunityReasonCode;
  signalValue: number | null;
  thresholdValue: number | null;
};

export type CountyAgeAlignmentRecord = {
  countySlug: string;
  ageBand: DetailAgeBand;
  currentChildren: number;
  preferenceMatchingHomes: number;
  childrenPerMatchingHome: number | null;
  limitedData: boolean;
  recruitmentEvidence: boolean;
  statewideP75Threshold: number | null;
};

export type CountyPlacementFlowRecord = {
  originCountySlug: string;
  destinationCountyName: string;
  placementCount: number;
  placementShare: number;
  isLocal: boolean;
};

export type CountyInvestigationQuestionRecord = {
  countySlug: string;
  displayOrder: number;
  questionText: string;
};
