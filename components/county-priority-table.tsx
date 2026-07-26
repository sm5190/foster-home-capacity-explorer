"use client";
import Link from "next/link";

import { buildCountyListHref, getNextSortDirection } from "../lib/county-query";
import {
  formatDecimal,
  formatInteger,
  formatPercentage,
} from "../lib/formatters";
import type {
  CountyListQuery,
  CountySort,
  CountySummary,
  Focus,
} from "../lib/schemas";
import { OpportunityBadge } from "./opportunity-badge";

import { getOpportunitySummary } from "../lib/opportunity-copy";

type CountyPriorityTableProps = {
  counties: readonly CountySummary[];
  focus: Focus;
  query: CountyListQuery;
  activeCountySlug?: string | null;
  onCountyActivate?: (countySlug: string) => void;
};

type SortHeaderProps = {
  label: string;
  sort: CountySort;
  query: CountyListQuery;
  numeric?: boolean;
};

function SortHeader({ label, sort, query, numeric = false }: SortHeaderProps) {
  const isActive = query.sort === sort;

  const direction = getNextSortDirection(query, sort);

  const ariaSort = isActive
    ? query.direction === "asc"
      ? "ascending"
      : "descending"
    : "none";

  return (
    <th
      aria-sort={ariaSort}
      className={numeric ? "numeric-column" : undefined}
      scope="col"
    >
      <Link
        className="sort-link"
        href={buildCountyListHref(query, {
          sort,
          direction,
        })}
      >
        <span>{label}</span>

        <span aria-hidden="true" className="sort-indicator">
          {isActive ? (query.direction === "asc" ? "↑" : "↓") : "↕"}
        </span>
      </Link>
    </th>
  );
}

export function CountyPriorityTable({
  counties,
  focus,
  query,
  activeCountySlug = null,
  onCountyActivate,
}: CountyPriorityTableProps) {
  const isRecruitment = focus === "recruitment";

  return (
    <div className="table-region">
      <table className="data-table">
        <caption className="sr-only">
          Illinois counties ranked by{" "}
          {isRecruitment ? "recruitment" : "existing-home engagement"}{" "}
          opportunity
        </caption>

        <thead>
          {isRecruitment ? (
            <tr>
              <SortHeader label="County" query={query} sort="county" />

              <SortHeader
                label="Children currently in care"
                numeric
                query={query}
                sort="childrenCurrentlyInCare"
              />

              <SortHeader
                label="Current foster homes"
                numeric
                query={query}
                sort="currentFosterHomes"
              />

              <SortHeader
                label="Children per current home"
                numeric
                query={query}
                sort="childrenPerCurrentHome"
              />

              <SortHeader
                label="Local foster-home placements"
                numeric
                query={query}
                sort="localPlacementRate"
              />

              <SortHeader
                label="Recruitment signal"
                query={query}
                sort="priority"
              />
            </tr>
          ) : (
            <tr>
              <SortHeader label="County" query={query} sort="county" />

              <SortHeader
                label="Current foster homes"
                numeric
                query={query}
                sort="currentFosterHomes"
              />

              {/* <th className="numeric-column" scope="col">
                Homes with recent activity
              </th> */}

              <SortHeader
                label="Homes without recent activity"
                numeric
                query={query}
                sort="homesWithoutRecentActivity"
              />

              <SortHeader
                label="Median active-day rate"
                numeric
                query={query}
                sort="medianObservedActiveDayRate"
              />

              <SortHeader
                label="Renewals within 90 days"
                numeric
                query={query}
                sort="renewalsWithin90Days"
              />

              <SortHeader
                label="Renewing + no recent activity"
                sort="renewalsWithoutRecentActivity"
                query={query}
                numeric
              />

              <SortHeader
                label="Engagement signal"
                query={query}
                sort="priority"
              />
            </tr>
          )}
        </thead>

        <tbody>
          {counties.map((county) => {
            const opportunity = isRecruitment
              ? county.recruitment
              : county.engagement;

            const evidence = opportunity.reasons
              .map((reason) => reason.label)
              .join("; ");

            return (
              <tr
                className={
                  activeCountySlug === county.countySlug
                    ? "is-active"
                    : undefined
                }
                id={`county-row-${county.countySlug}`}
                key={county.countySlug}
                onFocusCapture={() => {
                  onCountyActivate?.(county.countySlug);
                }}
                onMouseEnter={() => {
                  onCountyActivate?.(county.countySlug);
                }}
              >
                <th scope="row">
                  <Link
                    className="county-link"
                    href={`/county/${county.countySlug}`}
                  >
                    {county.countyName}
                  </Link>
                </th>

                {isRecruitment ? (
                  <>
                    <td className="numeric-column">
                      {formatInteger(county.childrenCurrentlyInCare)}
                    </td>

                    <td className="numeric-column">
                      {formatInteger(county.currentFosterHomes)}
                    </td>

                    <td className="numeric-column">
                      {formatDecimal(county.childrenPerCurrentHome, 1)}
                    </td>

                    <td className="numeric-column">
                      <span>{formatPercentage(county.localPlacementRate)}</span>

                      <span className="table-secondary">
                        {formatInteger(county.localFosterPlacements)}
                        {" of "}
                        {formatInteger(county.currentFosterPlacements)}
                      </span>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="numeric-column">
                      {formatInteger(county.currentFosterHomes)}
                    </td>

                    {/* <td className="numeric-column">
                      {formatInteger(county.homesWithRecentActivity)}
                    </td> */}

                    <td className="numeric-column">
                      {formatInteger(county.homesWithoutRecentActivity)}
                    </td>

                    <td className="numeric-column">
                      {formatPercentage(county.medianObservedActiveDayRate)}
                    </td>

                    <td className="numeric-column">
                      {formatInteger(county.renewalsWithin90Days)}
                    </td>

                    <td className="numeric-column">
                      {formatInteger(county.renewalsWithoutRecentActivity)}
                    </td>
                  </>
                )}

                <td>
                  <OpportunityBadge focus={focus} level={opportunity.level} />

                  <p className="table-evidence">
                    {getOpportunitySummary(focus, opportunity.level)}
                  </p>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
