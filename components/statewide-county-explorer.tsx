"use client";

import { useState } from "react";

import dynamic from "next/dynamic";
import Link from "next/link";

import { formatInteger } from "../lib/formatters";

import type { CountyListQuery, CountySummary } from "../lib/schemas";

import { CountyPriorityTable } from "./county-priority-table";

type StatewideCountyExplorerProps = {
  mapCounties: readonly CountySummary[];
  counties: readonly CountySummary[];
  query: CountyListQuery;
  totalCount: number;
};

const AGE_LABELS = {
  all: "all ages",
  "0-5": "ages 0 to 5",
  "6-12": "ages 6 to 12",
  "13-17": "ages 13 to 17",
} as const;

const IllinoisPriorityMap = dynamic(
  () =>
    import("./illinois-priority-map").then(
      (module) => module.IllinoisPriorityMap,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="county-map county-map--loading" role="status">
        Loading Illinois county map…
      </div>
    ),
  },
);

export function StatewideCountyExplorer({
  mapCounties,
  counties,
  query,
  totalCount,
}: StatewideCountyExplorerProps) {
  const [activeCountySlug, setActiveCountySlug] = useState<string | null>(null);

  const isRecruitment = query.focus === "recruitment";

  const focusLabel = isRecruitment ? "Recruitment" : "Existing-home engagement";

  const tableHeading = isRecruitment
    ? "Recruitment priorities by county"
    : "Retention and engagement indicators by county";

  const tableDescription = isRecruitment
    ? `Showing recruitment indicators for ` +
      `${AGE_LABELS[query.age]}. ` +
      `Limited-data counties remain visible but are not elevated solely by unstable percentages.`
    : `Compare recent provider activity, upcoming renewals, ` +
      `the intersection of renewal timing with no recent activity, ` +
      `and observed active-day rates. All counties remain visible ` +
      `for statewide context, including counties without an elevated signal.`;

  return (
    <>
      <section aria-labelledby="county-map-heading" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Geographic view</p>

            <h2 id="county-map-heading">Illinois county priorities</h2>

            <p>
              Explore where current opportunity signals appear geographically,
              then inspect the exact values in the county table.
            </p>
          </div>
        </div>

        <IllinoisPriorityMap
          activeCountySlug={activeCountySlug}
          age={isRecruitment ? query.age : "all"}
          counties={mapCounties}
          focus={query.focus}
          onCountyActivate={setActiveCountySlug}
          search={query.search}
        />
      </section>

      <section
        aria-labelledby="county-priorities-heading"
        className="content-section"
        id="county-priorities"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">{focusLabel}</p>

            <h2 id="county-priorities-heading">{tableHeading}</h2>

            <p>{tableDescription}</p>
          </div>

          <p className="result-count">
            {formatInteger(totalCount)}{" "}
            {totalCount === 1 ? "county" : "counties"}
          </p>
        </div>

        {counties.length > 0 ? (
          <CountyPriorityTable
            activeCountySlug={activeCountySlug}
            counties={counties}
            focus={query.focus}
            onCountyActivate={setActiveCountySlug}
            query={query}
          />
        ) : (
          <div className="empty-table-state">
            <h3>No counties match the current search</h3>

            <p>Try a broader county name or reset the current filters.</p>

            <Link className="button button--primary" href="/">
              Reset filters
            </Link>
          </div>
        )}
      </section>
    </>
  );
}
