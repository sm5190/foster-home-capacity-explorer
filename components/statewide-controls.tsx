"use client";

import { useState } from "react";

import Link from "next/link";

import type {
  AgeFilter,
  CountyListQuery,
  CountySort,
  Focus,
} from "../lib/schemas";

type StatewideControlsProps = {
  query: CountyListQuery;
};

type SortOption = {
  value: CountySort;
  label: string;
};

const RECRUITMENT_SORT_OPTIONS: readonly SortOption[] = [
  {
    value: "priority",
    label: "Opportunity priority",
  },
  {
    value: "county",
    label: "County name",
  },
  {
    value: "childrenCurrentlyInCare",
    label: "Children currently in care",
  },
  {
    value: "currentFosterHomes",
    label: "Current foster homes",
  },
  {
    value: "childrenPerCurrentHome",
    label: "Children per current home",
  },
  {
    value: "localPlacementRate",
    label: "Local placement rate",
  },
];

const ENGAGEMENT_SORT_OPTIONS: readonly SortOption[] = [
  {
    value: "priority",
    label: "Engagement priority",
  },
  {
    value: "county",
    label: "County name",
  },
  {
    value: "currentFosterHomes",
    label: "Current foster homes",
  },
  {
    value: "homesWithoutRecentActivity",
    label: "Homes without recent activity",
  },
  {
    value: "medianObservedActiveDayRate",
    label: "Median active-day rate",
  },
  {
    value: "renewalsWithin90Days",
    label: "Renewals within 90 days",
  },
];

function getSortOptions(focus: Focus): readonly SortOption[] {
  return focus === "recruitment"
    ? RECRUITMENT_SORT_OPTIONS
    : ENGAGEMENT_SORT_OPTIONS;
}

function isSortAvailable(focus: Focus, sort: CountySort): boolean {
  return getSortOptions(focus).some((option) => option.value === sort);
}

export function StatewideControls({ query }: StatewideControlsProps) {
  const [focus, setFocus] = useState<Focus>(query.focus);

  const [age, setAge] = useState<AgeFilter>(
    query.focus === "engagement" ? "all" : query.age,
  );

  const [sort, setSort] = useState<CountySort>(
    isSortAvailable(query.focus, query.sort) ? query.sort : "priority",
  );

  const sortOptions = getSortOptions(focus);

  function handleFocusChange(nextFocus: Focus): void {
    setFocus(nextFocus);

    if (nextFocus === "engagement") {
      setAge("all");
    }

    if (!isSortAvailable(nextFocus, sort)) {
      setSort("priority");
    }
  }

  return (
    <form action="/" className="controls-panel" method="get">
      <fieldset className="filter-group">
        <legend>Analysis focus</legend>

        <div className="focus-toggle">
          <label className="focus-option">
            <input
              checked={focus === "recruitment"}
              name="focus"
              onChange={() => {
                handleFocusChange("recruitment");
              }}
              type="radio"
              value="recruitment"
            />

            <span>Recruitment</span>
          </label>

          <label className="focus-option">
            <input
              checked={focus === "engagement"}
              name="focus"
              onChange={() => {
                handleFocusChange("engagement");
              }}
              type="radio"
              value="engagement"
            />

            <span>Existing-home engagement</span>
          </label>
        </div>
      </fieldset>

      <div
        className={[
          "filter-grid",
          focus === "engagement" ? "filter-grid--engagement" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <label className="filter-field">
          <span>County search</span>

          <input
            className="form-control"
            defaultValue={query.search}
            name="search"
            placeholder="Search county name"
            type="search"
          />
        </label>

        {focus === "recruitment" ? (
          <label className="filter-field">
            <span>Age group</span>

            <select
              aria-describedby="analysis-filter-note"
              className="form-control"
              name="age"
              onChange={(event) => {
                setAge(event.target.value as AgeFilter);
              }}
              value={age}
            >
              <option value="all">All ages</option>

              <option value="0-5">Ages 0 to 5</option>

              <option value="6-12">Ages 6 to 12</option>

              <option value="13-17">Ages 13 to 17</option>
            </select>
          </label>
        ) : (
          <input name="age" type="hidden" value="all" />
        )}

        <label className="filter-field">
          <span>Sort by</span>

          <select
            className="form-control"
            name="sort"
            onChange={(event) => {
              setSort(event.target.value as CountySort);
            }}
            value={sort}
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-field">
          <span>Direction</span>

          <select
            className="form-control"
            defaultValue={query.direction}
            name="direction"
          >
            <option value="desc">Highest first</option>

            <option value="asc">Lowest first</option>
          </select>
        </label>
      </div>

      <p className="filter-note" id="analysis-filter-note">
        {focus === "recruitment"
          ? "The age-group filter changes recruitment evidence only. Provider preferences do not represent available beds."
          : "Engagement indicators use recent placement activity, renewal timing, and observed active-day rates. Age groups do not affect engagement results."}
      </p>

      <div className="form-actions">
        <button className="button button--primary" type="submit">
          Apply filters
        </button>

        <Link className="button button--secondary" href="/">
          Reset
        </Link>
      </div>
    </form>
  );
}
