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

function getRatioDecimalPlaces(...values: Array<number | null>): number {
  const availableValues = values.filter(
    (value): value is number => value !== null,
  );

  if (availableValues.length === 0) {
    return 1;
  }

  const largestAbsoluteValue = Math.max(
    ...availableValues.map((value) => Math.abs(value)),
  );

  return largestAbsoluteValue < 1 ? 2 : 1;
}

function formatRatio(value: number | null, decimalPlaces: number): string {
  if (value === null) {
    return "Not available";
  }

  return formatDecimal(value, decimalPlaces);
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

  const decimalPlaces = getRatioDecimalPlaces(
    twelveMonthsAgoRatio,
    currentRatio,
  );

  const percentageChange = formatPercentage(Math.abs(percentChange));

  const changeDescription =
    direction === "stable"
      ? `remained broadly stable, changing by ${percentageChange}`
      : direction === "increasing"
        ? `increased by ${percentageChange}`
        : `decreased by ${percentageChange}`;

  return (
    `${countyName} County's children-per-home pressure ` +
    `${changeDescription}, from ` +
    `${formatRatio(twelveMonthsAgoRatio, decimalPlaces)} to ` +
    `${formatRatio(
      currentRatio,
      decimalPlaces,
    )} children per licensed home over the past 12 months.`
  );
}

export function CapacityTrendChart({
  countyName,
  points,
  summary,
}: CapacityTrendChartProps) {
  const summaryText = buildSummaryText(countyName, summary);

  const yAxisDecimalPlaces = getRatioDecimalPlaces(
    ...points.map((point) => point.childrenPerCurrentHome),
  );

  return (
    <div className="trend-card">
      <div aria-label={summaryText} className="trend-chart" role="img">
        <ResponsiveContainer height={320} width="100%">
          <LineChart
            data={points}
            margin={{
              top: 12,
              right: 36,
              bottom: 12,
              left: 4,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />

            <XAxis
              dataKey="snapshotDate"
              height={48}
              interval={0}
              minTickGap={0}
              padding={{
                left: 8,
                right: 16,
              }}
              tick={{
                fontSize: 12,
              }}
              tickFormatter={formatMonth}
              tickMargin={10}
            />

            <YAxis
              allowDecimals
              domain={[0, "auto"]}
              tick={{
                fontSize: 12,
              }}
              tickFormatter={(value: number) =>
                value.toFixed(yAxisDecimalPlaces)
              }
              width={52}
            />

            <Tooltip
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as
                  CountyMonthlyTrendPoint | undefined;

                if (!active || !point) {
                  return null;
                }

                const pointDecimalPlaces = getRatioDecimalPlaces(
                  point.childrenPerCurrentHome,
                );

                return (
                  <div className="trend-tooltip">
                    <strong>{formatMonth(point.snapshotDate)}</strong>

                    <span>
                      {formatRatio(
                        point.childrenPerCurrentHome,
                        pointDecimalPlaces,
                      )}{" "}
                      children per licensed home
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
              activeDot={{
                r: 6,
              }}
              connectNulls={false}
              dataKey="childrenPerCurrentHome"
              dot={{
                r: 4,
                fill: "var(--surface)",
                strokeWidth: 2,
              }}
              isAnimationActive={false}
              name="Children per licensed home"
              stroke="var(--primary)"
              strokeWidth={3}
              type="monotone"
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
