"use client";

import { useMemo, useRef, useState } from "react";

import { geoMercator, geoPath } from "d3-geo";

import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";

import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  formatDecimal,
  formatInteger,
  formatPercentage,
} from "../lib/formatters";

import illinoisCountyData from "../lib/map/illinois-counties.json";

import type {
  AgeFilter,
  CountySummary,
  Focus,
  OpportunityLevel,
} from "../lib/schemas";

import { OpportunityBadge } from "./opportunity-badge";

type IllinoisCountyProperties = {
  fips: string;
  countyName: string;
  countySlug: string;
};

type IllinoisCountyCollection = FeatureCollection<
  Polygon | MultiPolygon,
  IllinoisCountyProperties
>;

type IllinoisPriorityMapProps = {
  counties: readonly CountySummary[];
  focus: Focus;
  age: AgeFilter;
  search: string;
  activeCountySlug: string | null;
  onCountyActivate: (countySlug: string) => void;
};

const MAP_WIDTH = 720;
const MAP_HEIGHT = 820;

const countyCollection = illinoisCountyData as IllinoisCountyCollection;

const countyFeatures = [...countyCollection.features].sort((first, second) =>
  first.properties.fips.localeCompare(second.properties.fips),
);

const projection = geoMercator().fitExtent(
  [
    [18, 18],
    [MAP_WIDTH - 18, MAP_HEIGHT - 18],
  ],
  countyCollection,
);

const pathGenerator = geoPath(projection);

const AGE_LABELS: Record<AgeFilter, string> = {
  all: "all ages",
  "0-5": "ages 0 to 5",
  "6-12": "ages 6 to 12",
  "13-17": "ages 13 to 17",
};

const LEVEL_LABELS: Record<OpportunityLevel, string> = {
  higher: "Higher opportunity",
  possible: "Possible opportunity",
  review: "No elevated signal",
  limited: "Limited data",
};

const MAP_FILL_COLORS: Record<OpportunityLevel, string> = {
  higher: "#e78aa0",
  possible: "#f3c77a",
  review: "#8fb6f5",
  limited: "#d8e0ea",
};
const OPPORTUNITY_LEVELS = ["higher", "possible", "review", "limited"] as const;

function getOpportunity(county: CountySummary, focus: Focus) {
  return focus === "recruitment" ? county.recruitment : county.engagement;
}

function buildCountyAriaLabel(county: CountySummary, focus: Focus): string {
  const opportunity = getOpportunity(county, focus);

  const focusLabel =
    focus === "recruitment" ? "recruitment" : "existing-home engagement";

  return (
    `${county.countyName} County, ` +
    `${LEVEL_LABELS[opportunity.level].toLowerCase()} for ` +
    `${focusLabel}. Open county brief.`
  );
}

function MapMetrics({
  county,
  focus,
}: {
  county: CountySummary;
  focus: Focus;
}) {
  if (focus === "recruitment") {
    return (
      <dl className="county-map__metrics">
        <div>
          <dt>Children currently in care</dt>
          <dd>{formatInteger(county.childrenCurrentlyInCare)}</dd>
        </div>

        <div>
          <dt>Current foster homes</dt>
          <dd>{formatInteger(county.currentFosterHomes)}</dd>
        </div>

        <div>
          <dt>Children per current home</dt>
          <dd>{formatDecimal(county.childrenPerCurrentHome, 1)}</dd>
        </div>

        <div>
          <dt>Placed near home community</dt>
          <dd>{formatPercentage(county.localPlacementRate)}</dd>
        </div>
      </dl>
    );
  }

  return (
    <dl className="county-map__metrics">
      <div>
        <dt>Current foster homes</dt>
        <dd>{formatInteger(county.currentFosterHomes)}</dd>
      </div>

      <div>
        <dt>No recent activity</dt>
        <dd>{formatInteger(county.homesWithoutRecentActivity)}</dd>
      </div>

      <div>
        <dt>Renewing within 90 days</dt>
        <dd>{formatInteger(county.renewalsWithin90Days)}</dd>
      </div>

      <div>
        <dt>Renewing plus no activity</dt>
        <dd>{formatInteger(county.renewalsWithoutRecentActivity)}</dd>
      </div>
    </dl>
  );
}

export function IllinoisPriorityMap({
  counties,
  focus,
  age,
  search,
  activeCountySlug,
  onCountyActivate,
}: IllinoisPriorityMapProps) {
  const router = useRouter();

  const [selectedOpportunityLevel, setSelectedOpportunityLevel] =
    useState<OpportunityLevel | null>(null);

  const countyRefs = useRef<Array<SVGPathElement | null>>([]);

  const countiesBySlug = useMemo(
    () => new Map(counties.map((county) => [county.countySlug, county])),
    [counties],
  );

  const normalizedSearch = search.trim().toLowerCase();

  const activeCounty =
    activeCountySlug === null
      ? null
      : (countiesBySlug.get(activeCountySlug) ?? null);

  const higherCount = counties.filter(
    (county) => getOpportunity(county, focus).level === "higher",
  ).length;

  const possibleCount = counties.filter(
    (county) => getOpportunity(county, focus).level === "possible",
  ).length;

  const focusLabel =
    focus === "recruitment"
      ? `recruitment for ${AGE_LABELS[age]}`
      : "existing-home engagement";

  function focusCountyAtIndex(index: number) {
    const wrappedIndex =
      (index + countyFeatures.length) % countyFeatures.length;

    countyRefs.current[wrappedIndex]?.focus();
  }

  function toggleOpportunityLevel(level: OpportunityLevel) {
    setSelectedOpportunityLevel(
      selectedOpportunityLevel === level ? null : level,
    );
  }

  return (
    <div className="county-map">
      <p className="county-map__insight">
        <strong>{formatInteger(higherCount)}</strong> counties show higher{" "}
        {focusLabel} opportunity and{" "}
        <strong>{formatInteger(possibleCount)}</strong> show possible
        opportunity.
      </p>

      <a className="skip-map-link" href="#county-priorities">
        Skip the map and go to the county table
      </a>

      <div className="county-map__layout">
        <div className="county-map__visual">
          <svg
            aria-label={`Interactive Illinois county map showing ${focusLabel} opportunity`}
            className="county-map__svg"
            role="group"
            viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
          >
            {countyFeatures.map((countyFeature, index) => {
              const countySlug = countyFeature.properties.countySlug;

              const county = countiesBySlug.get(countySlug);

              if (!county) {
                return null;
              }

              const opportunity = getOpportunity(county, focus);

              const pathData = pathGenerator(countyFeature);

              if (!pathData) {
                return null;
              }

              const isActive = countySlug === activeCountySlug;

              const isSearchMatch =
                normalizedSearch.length === 0 ||
                county.countyName.toLowerCase().includes(normalizedSearch);

              const isOpportunityMatch =
                selectedOpportunityLevel === null ||
                opportunity.level === selectedOpportunityLevel;

              const isDimmed = !isSearchMatch || !isOpportunityMatch;

              const className = [
                "county-map__shape",
                `county-map__shape--${opportunity.level}`,
                isActive ? "is-active" : "",
                isDimmed ? "is-dimmed" : "",
              ]
                .filter(Boolean)
                .join(" ");

              const titleText =
                `${county.countyName} County: ` +
                LEVEL_LABELS[opportunity.level];

              return (
                <path
                  aria-label={buildCountyAriaLabel(county, focus)}
                  className={className}
                  d={pathData}
                  data-county-slug={countySlug}
                  fill={MAP_FILL_COLORS[opportunity.level]}
                  key={countyFeature.properties.fips}
                  onClick={() => {
                    router.push(`/county/${countySlug}`);
                  }}
                  onFocus={() => {
                    onCountyActivate(countySlug);
                  }}
                  onKeyDown={(event) => {
                    if (
                      event.key === "ArrowRight" ||
                      event.key === "ArrowDown"
                    ) {
                      event.preventDefault();

                      focusCountyAtIndex(index + 1);

                      return;
                    }

                    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                      event.preventDefault();

                      focusCountyAtIndex(index - 1);

                      return;
                    }

                    if (event.key === "Home") {
                      event.preventDefault();

                      focusCountyAtIndex(0);

                      return;
                    }

                    if (event.key === "End") {
                      event.preventDefault();

                      focusCountyAtIndex(countyFeatures.length - 1);

                      return;
                    }

                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();

                      router.push(`/county/${countySlug}`);
                    }
                  }}
                  onMouseEnter={() => {
                    onCountyActivate(countySlug);
                  }}
                  ref={(element) => {
                    countyRefs.current[index] = element;
                  }}
                  role="link"
                  stroke="#ffffff"
                  tabIndex={index === 0 ? 0 : -1}
                >
                  <title>{titleText}</title>
                </path>
              );
            })}
          </svg>

          <p className="county-map__help">
            Hover or focus a county to inspect it. Use the arrow keys to move
            between county shapes and press Enter to open the county brief.
          </p>
        </div>

        <aside
          aria-label="Selected county details"
          className="county-map__details"
        >
          {activeCounty ? (
            <>
              <p className="eyebrow">Selected county</p>

              <h3>{activeCounty.countyName} County</h3>

              <OpportunityBadge
                focus={focus}
                level={getOpportunity(activeCounty, focus).level}
              />

              <MapMetrics county={activeCounty} focus={focus} />

              <div className="county-map__actions">
                <Link
                  className="button button--primary"
                  href={`/county/${activeCounty.countySlug}`}
                >
                  Open county brief
                </Link>

                <a
                  className="button button--secondary"
                  href={`#county-row-${activeCounty.countySlug}`}
                >
                  Find in table
                </a>
              </div>
            </>
          ) : (
            <>
              <p className="eyebrow">Explore the map</p>

              <h3>Select a county</h3>

              <p>
                Hover, focus, or select a county to see its current evidence and
                open the full county brief.
              </p>
            </>
          )}
        </aside>
      </div>

      <div
        aria-label="Filter counties by opportunity level"
        className="county-map__legend"
        role="group"
      >
        {OPPORTUNITY_LEVELS.map((level) => {
          const isSelected = selectedOpportunityLevel === level;

          return (
            <button
              aria-pressed={isSelected}
              className={[
                "county-map__legend-button",
                isSelected ? "is-selected" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              key={level}
              onClick={() => {
                toggleOpportunityLevel(level);
              }}
              type="button"
            >
              <span
                aria-hidden="true"
                className={`county-map__legend-swatch county-map__legend-swatch--${level}`}
                style={{
                  backgroundColor: MAP_FILL_COLORS[level],
                }}
              />

              {LEVEL_LABELS[level]}
            </button>
          );
        })}

        {selectedOpportunityLevel !== null ? (
          <button
            className="county-map__legend-clear"
            onClick={() => {
              setSelectedOpportunityLevel(null);
            }}
            type="button"
          >
            Show all counties
          </button>
        ) : null}
      </div>

      <p className="method-note">
        County boundaries are displayed for geographic orientation. Opportunity
        labels are analytical signals, not official county grades.
      </p>
    </div>
  );
}
