import { z } from "zod";

/*
 * Shared primitive schemas
 */

const nonnegativeIntegerSchema = z.number().int().nonnegative();

const nullableNonnegativeNumberSchema = z.number().nonnegative().nullable();

const nullableRateSchema = z.number().min(0).max(1).nullable();

/*
 * Query and route values
 */

export const focusSchema = z.enum(["recruitment", "engagement"]);

export const ageFilterSchema = z.enum(["all", "0-5", "6-12", "13-17"]);

export const detailAgeBandSchema = z.enum(["0-5", "6-12", "13-17", "unknown"]);

export const opportunityLevelSchema = z.enum([
  "higher",
  "possible",
  "review",
  "limited",
]);

export const primaryOpportunitySchema = z.enum([
  "recruitment",
  "engagement",
  "both",
  "review",
]);

export const sortDirectionSchema = z.enum(["asc", "desc"]);

export const countySortSchema = z.enum([
  "priority",
  "county",
  "childrenCurrentlyInCare",
  "currentFosterHomes",
  "childrenPerCurrentHome",
  "localPlacementRate",
  "homesWithoutRecentActivity",
  "medianObservedActiveDayRate",
  "renewalsWithin90Days",
]);

export const countySlugSchema = z
  .string()
  .trim()
  .min(1)
  .max(100)
  .regex(
    /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
    "County slug must contain lowercase letters, numbers, and hyphens only.",
  );

export const countyListQuerySchema = z
  .object({
    focus: focusSchema.default("recruitment"),
    age: ageFilterSchema.default("all"),
    search: z.string().trim().max(100).default(""),
    sort: countySortSchema.default("priority"),
    direction: sortDirectionSchema.default("desc"),
  })
  .strict();

export const countyRouteParamsSchema = z
  .object({
    countySlug: countySlugSchema,
  })
  .strict();

/*
 * Public build metadata
 */

export const publicMetadataSchema = z
  .object({
    schemaVersion: z.string().trim().min(1),
    reportingCutoff: z.iso.date(),
    observationStart: z.iso.date(),
    buildStatus: z.literal("complete"),
  })
  .strict();

/*
 * Opportunity evidence
 */

export const opportunityReasonCodeSchema = z.enum([
  "high_children_per_current_home",
  "high_out_of_county_foster_rate",
  "high_children_per_preference_matching_home",
  "high_share_without_recent_activity",
  "low_median_observed_active_day_rate",
  "high_renewal_share_90_days",
]);

export const opportunityReasonSchema = z
  .object({
    code: opportunityReasonCodeSchema,
    label: z.string().trim().min(1),
    value: nullableNonnegativeNumberSchema,
    threshold: nullableNonnegativeNumberSchema,
  })
  .strict();

export const opportunitySummarySchema = z
  .object({
    level: opportunityLevelSchema,
    signalCount: z.number().int().min(0).max(3),
    reasons: z.array(opportunityReasonSchema).max(3),
  })
  .strict()
  .superRefine((value, context) => {
    if (value.reasons.length !== value.signalCount) {
      context.addIssue({
        code: "custom",
        path: ["reasons"],
        message:
          "The number of opportunity reasons must equal the signal count.",
      });
    }
  });

/*
 * Statewide aggregate response
 */

export const statewideSummarySchema = z
  .object({
    reportingCutoff: z.iso.date(),
    observationStart: z.iso.date(),

    childrenCurrentlyInCare: nonnegativeIntegerSchema,

    currentKinPlacements: nonnegativeIntegerSchema,
    currentFosterHomePlacements: nonnegativeIntegerSchema,
    currentNonfamilyPlacements: nonnegativeIntegerSchema,

    currentFosterHomes: nonnegativeIntegerSchema,
    homesWithCurrentPlacement: nonnegativeIntegerSchema,
    homesWithRecentActivity: nonnegativeIntegerSchema,
    homesWithoutRecentActivity: nonnegativeIntegerSchema,

    localFosterPlacements: nonnegativeIntegerSchema,
    outOfCountyFosterPlacements: nonnegativeIntegerSchema,
    localPlacementRate: nullableRateSchema,

    medianObservedActiveDayRate: nullableRateSchema,
  })
  .strict();

/*
 * County summary contract
 */

export const countySummarySchema = z
  .object({
    countySlug: countySlugSchema,
    countyName: z.string().trim().min(1),

    childrenCurrentlyInCare: nonnegativeIntegerSchema,
    currentFosterHomes: nonnegativeIntegerSchema,
    childrenPerCurrentHome: nullableNonnegativeNumberSchema,

    currentFosterPlacements: nonnegativeIntegerSchema,
    localFosterPlacements: nonnegativeIntegerSchema,
    outOfCountyFosterPlacements: nonnegativeIntegerSchema,
    localPlacementRate: nullableRateSchema,

    homesWithCurrentPlacement: nonnegativeIntegerSchema,
    homesWithRecentActivity: nonnegativeIntegerSchema,
    homesWithoutRecentActivity: nonnegativeIntegerSchema,
    medianObservedActiveDayRate: nullableRateSchema,
    renewalsWithin90Days: nonnegativeIntegerSchema,

    recruitment: opportunitySummarySchema,
    engagement: opportunitySummarySchema,

    primaryOpportunity: primaryOpportunitySchema,
    limitedData: z.boolean(),
  })
  .strict();

/*
 * County placement-setting breakdown
 *
 * This is required by the product contract, but the current aggregate
 * database still needs county-level kin and nonfamily counts added.
 */

export const placementCategorySchema = z
  .object({
    count: nonnegativeIntegerSchema,
    share: nullableRateSchema,
  })
  .strict();

export const countyPlacementSettingsSchema = z
  .object({
    totalCurrentPlacements: nonnegativeIntegerSchema,
    kin: placementCategorySchema,
    fosterHome: placementCategorySchema,
    nonfamily: placementCategorySchema,
  })
  .strict()
  .superRefine((value, context) => {
    const categoryTotal =
      value.kin.count + value.fosterHome.count + value.nonfamily.count;

    if (categoryTotal !== value.totalCurrentPlacements) {
      context.addIssue({
        code: "custom",
        path: ["totalCurrentPlacements"],
        message:
          "Kin, foster-home, and nonfamily counts must reconcile to total current placements.",
      });
    }
  });

/*
 * County age-preference alignment
 */

export const countyAgeAlignmentSchema = z
  .object({
    ageBand: detailAgeBandSchema,
    currentChildren: nonnegativeIntegerSchema,
    preferenceMatchingHomes: nonnegativeIntegerSchema,
    childrenPerMatchingHome: nullableNonnegativeNumberSchema,
    limitedData: z.boolean(),
    recruitmentEvidence: z.boolean(),
    statewideP75Threshold: nullableNonnegativeNumberSchema,
  })
  .strict();

/*
 * County placement flow
 */

export const countyPlacementFlowSchema = z
  .object({
    destinationCountyName: z.string().trim().min(1),
    placementCount: nonnegativeIntegerSchema,
    placementShare: z.number().min(0).max(1),
    isLocal: z.boolean(),
  })
  .strict();

/*
 * Investigation questions
 */

export const investigationQuestionSchema = z
  .object({
    displayOrder: z.number().int().min(1).max(5),
    questionText: z.string().trim().min(1),
  })
  .strict();

/*
 * API success responses
 */

export const countyListResponseSchema = z
  .object({
    metadata: publicMetadataSchema,
    query: countyListQuerySchema,
    statewide: statewideSummarySchema,
    counties: z.array(countySummarySchema),
    totalCount: nonnegativeIntegerSchema,
  })
  .strict()
  .superRefine((value, context) => {
    if (value.totalCount !== value.counties.length) {
      context.addIssue({
        code: "custom",
        path: ["totalCount"],
        message: "Total count must equal the number of returned counties.",
      });
    }
  });

export const countyDetailResponseSchema = z
  .object({
    metadata: publicMetadataSchema,
    diagnosis: z.string().trim().min(1),
    county: countySummarySchema,
    placementSettings: countyPlacementSettingsSchema,
    ageAlignment: z.array(countyAgeAlignmentSchema).min(3).max(4),
    placementFlows: z.array(countyPlacementFlowSchema),
    investigationQuestions: z.array(investigationQuestionSchema).min(3).max(5),
  })
  .strict()
  .superRefine((value, context) => {
    if (
      value.placementSettings.totalCurrentPlacements !==
      value.county.childrenCurrentlyInCare
    ) {
      context.addIssue({
        code: "custom",
        path: ["placementSettings", "totalCurrentPlacements"],
        message:
          "County placement totals must reconcile to children currently in care.",
      });
    }
  });

export const healthResponseSchema = z
  .object({
    status: z.literal("ok"),
    service: z.string().trim().min(1),
    schemaVersion: z.string().trim().min(1),
    dataCutoff: z.iso.date(),
    observationStart: z.iso.date(),
    buildStatus: z.literal("complete"),
    appVersion: z.string().trim().min(1),
    commitSha: z.string().trim().min(1).nullable(),
  })
  .strict();

/*
 * API error response
 */

export const apiErrorCodeSchema = z.enum([
  "INVALID_QUERY",
  "COUNTY_NOT_FOUND",
  "DATABASE_UNAVAILABLE",
  "INTERNAL_ERROR",
]);

export const apiErrorResponseSchema = z
  .object({
    error: z
      .object({
        code: apiErrorCodeSchema,
        message: z.string().trim().min(1),
      })
      .strict(),
    requestId: z.string().trim().min(1),
  })
  .strict();

/*
 * Inferred TypeScript types
 */

export type Focus = z.infer<typeof focusSchema>;

export type AgeFilter = z.infer<typeof ageFilterSchema>;

export type DetailAgeBand = z.infer<typeof detailAgeBandSchema>;

export type OpportunityLevel = z.infer<typeof opportunityLevelSchema>;

export type PrimaryOpportunity = z.infer<typeof primaryOpportunitySchema>;

export type SortDirection = z.infer<typeof sortDirectionSchema>;

export type CountySort = z.infer<typeof countySortSchema>;

export type CountyListQueryInput = z.input<typeof countyListQuerySchema>;

export type CountyListQuery = z.output<typeof countyListQuerySchema>;

export type PublicMetadata = z.infer<typeof publicMetadataSchema>;

export type OpportunityReasonCode = z.infer<typeof opportunityReasonCodeSchema>;

export type OpportunityReason = z.infer<typeof opportunityReasonSchema>;

export type OpportunitySummary = z.infer<typeof opportunitySummarySchema>;

export type StatewideSummary = z.infer<typeof statewideSummarySchema>;

export type CountySummary = z.infer<typeof countySummarySchema>;

export type CountyPlacementSettings = z.infer<
  typeof countyPlacementSettingsSchema
>;

export type CountyAgeAlignment = z.infer<typeof countyAgeAlignmentSchema>;

export type CountyPlacementFlow = z.infer<typeof countyPlacementFlowSchema>;

export type InvestigationQuestion = z.infer<typeof investigationQuestionSchema>;

export type CountyListResponse = z.infer<typeof countyListResponseSchema>;

export type CountyDetailResponse = z.infer<typeof countyDetailResponseSchema>;

export type HealthResponse = z.infer<typeof healthResponseSchema>;

export type ApiErrorCode = z.infer<typeof apiErrorCodeSchema>;

export type ApiErrorResponse = z.infer<typeof apiErrorResponseSchema>;
