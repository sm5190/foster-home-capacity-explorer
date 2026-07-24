import Link from "next/link";

import type { CountyListQuery } from "../lib/schemas";

type StatewideControlsProps = {
  query: CountyListQuery;
};

export function StatewideControls({ query }: StatewideControlsProps) {
  return (
    <form action="/" className="controls-panel" method="get">
      <fieldset className="filter-group">
        <legend>Analysis focus</legend>

        <div className="focus-toggle">
          <label className="focus-option">
            <input
              defaultChecked={query.focus === "recruitment"}
              name="focus"
              type="radio"
              value="recruitment"
            />

            <span>Recruitment</span>
          </label>

          <label className="focus-option">
            <input
              defaultChecked={query.focus === "engagement"}
              name="focus"
              type="radio"
              value="engagement"
            />

            <span>Existing-home engagement</span>
          </label>
        </div>
      </fieldset>

      <div className="filter-grid">
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

        <label className="filter-field">
          <span>Age group</span>

          <select
            aria-describedby="age-filter-note"
            className="form-control"
            defaultValue={query.age}
            name="age"
          >
            <option value="all">All ages</option>

            <option value="0-5">Ages 0 to 5</option>

            <option value="6-12">Ages 6 to 12</option>

            <option value="13-17">Ages 13 to 17</option>
          </select>
        </label>

        <label className="filter-field">
          <span>Sort by</span>

          <select
            className="form-control"
            defaultValue={query.sort}
            name="sort"
          >
            <option value="priority">Opportunity priority</option>

            <option value="county">County name</option>

            <option value="childrenCurrentlyInCare">
              Children currently in care
            </option>

            <option value="currentFosterHomes">Current foster homes</option>

            <option value="childrenPerCurrentHome">
              Children per current home
            </option>

            <option value="localPlacementRate">Local placement rate</option>

            <option value="homesWithoutRecentActivity">
              Homes without recent activity
            </option>

            <option value="medianObservedActiveDayRate">
              Median active-day rate
            </option>

            <option value="renewalsWithin90Days">
              Renewals within 90 days
            </option>
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

      <p className="filter-note" id="age-filter-note">
        The age-group filter changes recruitment evidence only. Provider
        preferences do not represent available beds.
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
