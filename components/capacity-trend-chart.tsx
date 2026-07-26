"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  formatDecimal,
  formatInteger,
  formatPercentage,
} from "../lib/formatters";

import type {
  CapacityTrendSummary,
  CountyMonthlyTrendPoint,
} from "../lib/schemas";

type CapacityTrendChartProps = {
  countyName: string;
  points: readonly CountyMonthlyTrendPoint[];
  summary: CapacityTrendSummary;
};

function formatMonth(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function buildSummaryText(
  countyName: string,
  summary: CapacityTrendSummary,
): string {
  const {
    twelveMonthsAgoRatio,
    currentRatio,
    absoluteChange,
    percentChange,
    direction,
  } = summary;

  if (
    twelveMonthsAgoRatio === null ||
    currentRatio === null ||
    absoluteChange === null ||
    percentChange === null
  ) {
    return (
      `A complete 12-month children-per-home comparison ` +
      `is not available for ${countyName} County.`
    );
  }

  const directionText =
    direction === "stable"
      ? "was broadly stable"
      : direction === "increasing"
        ? "increased"
        : "decreased";

  const percentageChange = formatPercentage(Math.abs(percentChange));

  const changeDescription =
    direction === "stable"
      ? `changed by ${percentageChange}`
      : `${directionText} by ${percentageChange}`;

  return (
    `${countyName} County's children-per-home pressure ` +
    `${changeDescription}, from ` +
    `${formatDecimal(twelveMonthsAgoRatio, 1)} to ` +
    `${formatDecimal(currentRatio, 1)} children per licensed ` +
    `home over the past 12 months.`
  );
}

export function CapacityTrendChart({
  countyName,
  points,
  summary,
}: CapacityTrendChartProps) {
  const summaryText = buildSummaryText(countyName, summary);

  return (
    <div className="trend-card">
      <div className="trend-chart" role="img" aria-label={summaryText}>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart
            data={points}
            margin={{
              top: 12,
              right: 20,
              bottom: 12,
              left: 0,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />

            <XAxis
              dataKey="snapshotDate"
              tickFormatter={formatMonth}
              interval={0}
              minTickGap={0}
              tickMargin={10}
            />

            <YAxis
              width={56}
              tickFormatter={(value: number) => formatDecimal(value, 1)}
            />

            <Tooltip
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as
                  CountyMonthlyTrendPoint | undefined;

                if (!active || !point) {
                  return null;
                }

                return (
                  <div className="trend-tooltip">
                    <strong>{formatMonth(point.snapshotDate)}</strong>

                    <span>
                      {formatDecimal(point.childrenPerCurrentHome, 1)} children
                      per licensed home
                    </span>

                    <span>
                      {formatInteger(point.childrenCurrentlyInCare)} children in
                      care
                    </span>

                    <span>
                      {formatInteger(point.currentFosterHomes)} licensed homes
                    </span>
                  </div>
                );
              }}
            />

            <Line
              type="monotone"
              dataKey="childrenPerCurrentHome"
              name="Children per licensed home"
              stroke="var(--primary)"
              strokeWidth={3}
              dot={{
                r: 4,
                fill: "var(--surface)",
                strokeWidth: 2,
              }}
              activeDot={{ r: 6 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="trend-summary">{summaryText}</p>

      <p className="method-note">
        This is a capacity-pressure indicator, not a calculation of available
        beds or vacancies.
      </p>
    </div>
  );
}
