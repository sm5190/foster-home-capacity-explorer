import Link from "next/link";

import {
  formatDecimal,
  formatInteger,
  formatPercentage,
} from "../lib/formatters";
import type { CountySummary } from "../lib/schemas";
import { OpportunityBadge } from "./opportunity-badge";

type CountyPriorityTableProps = {
  counties: readonly CountySummary[];
};

export function CountyPriorityTable({ counties }: CountyPriorityTableProps) {
  return (
    <div className="table-region">
      <table className="data-table">
        <caption className="sr-only">
          Illinois counties ranked by recruitment opportunity
        </caption>

        <thead>
          <tr>
            <th scope="col">County</th>

            <th className="numeric-column" scope="col">
              Children currently in care
            </th>

            <th className="numeric-column" scope="col">
              Current foster homes
            </th>

            <th className="numeric-column" scope="col">
              Children per current home
            </th>

            <th className="numeric-column" scope="col">
              Local foster-home placements
            </th>

            <th scope="col">Recruitment signal</th>
          </tr>
        </thead>

        <tbody>
          {counties.map((county) => {
            const evidence = county.recruitment.reasons
              .map((reason) => reason.label)
              .join("; ");

            return (
              <tr key={county.countySlug}>
                <th scope="row">
                  <Link
                    className="county-link"
                    href={`/county/${county.countySlug}`}
                  >
                    {county.countyName}
                  </Link>
                </th>

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

                <td>
                  <OpportunityBadge
                    focus="recruitment"
                    level={county.recruitment.level}
                  />

                  <p className="table-evidence">
                    {evidence || "No statewide recruitment threshold was met."}
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
