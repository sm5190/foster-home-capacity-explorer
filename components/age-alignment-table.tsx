import { formatDecimal, formatInteger } from "../lib/formatters";
import type { CountyAgeAlignment } from "../lib/schemas";

type AgeAlignmentTableProps = {
  rows: readonly CountyAgeAlignment[];
};

const AGE_BAND_LABELS: Record<CountyAgeAlignment["ageBand"], string> = {
  "0-5": "Ages 0 to 5",
  "6-12": "Ages 6 to 12",
  "13-17": "Ages 13 to 17",
  unknown: "Unknown age",
};

export function AgeAlignmentTable({ rows }: AgeAlignmentTableProps) {
  return (
    <>
      <div className="table-region">
        <table className="data-table data-table--compact">
          <caption className="sr-only">
            Current children and provider age-preference alignment
          </caption>

          <thead>
            <tr>
              <th scope="col">Age group</th>

              <th className="numeric-column" scope="col">
                Current children
              </th>

              <th className="numeric-column" scope="col">
                Homes whose preferences overlap this group
              </th>

              <th className="numeric-column" scope="col">
                Children per matching home
              </th>

              <th scope="col">Comparison</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row) => (
              <tr key={row.ageBand}>
                <th scope="row">{AGE_BAND_LABELS[row.ageBand]}</th>

                <td className="numeric-column">
                  {formatInteger(row.currentChildren)}
                </td>

                <td className="numeric-column">
                  {formatInteger(row.preferenceMatchingHomes)}
                </td>

                <td className="numeric-column">
                  {formatDecimal(row.childrenPerMatchingHome, 1)}
                </td>

                <td>
                  {row.limitedData ? (
                    <span className="text-status">Limited data</span>
                  ) : row.recruitmentEvidence ? (
                    <span className="text-status text-status--attention">
                      Above statewide 75th percentile
                    </span>
                  ) : (
                    <span className="text-status">
                      Below statewide 75th percentile
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="method-note">
        Preferences indicate the ages a currently licensed home is willing to
        consider. They do not indicate available beds or current availability.
      </p>
    </>
  );
}
