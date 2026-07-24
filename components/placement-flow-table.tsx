import { formatInteger, formatPercentage } from "../lib/formatters";
import type { CountyPlacementFlow } from "../lib/schemas";

type PlacementFlowTableProps = {
  flows: readonly CountyPlacementFlow[];
};

function selectDisplayedFlows(
  flows: readonly CountyPlacementFlow[],
): readonly CountyPlacementFlow[] {
  const topFlows = flows.slice(0, 8);

  const localFlow = flows.find((flow) => flow.isLocal);

  if (!localFlow || topFlows.some((flow) => flow.isLocal)) {
    return topFlows;
  }

  return [...topFlows, localFlow];
}

export function PlacementFlowTable({ flows }: PlacementFlowTableProps) {
  const displayedFlows = selectDisplayedFlows(flows);

  return (
    <div className="table-region">
      <table className="data-table data-table--compact">
        <caption className="sr-only">
          Top destination counties for current foster-home placements
        </caption>

        <thead>
          <tr>
            <th scope="col">Placement county</th>

            <th className="numeric-column" scope="col">
              Current placements
            </th>

            <th className="numeric-column" scope="col">
              Share
            </th>
          </tr>
        </thead>

        <tbody>
          {displayedFlows.map((flow) => (
            <tr key={`${flow.destinationCountyName}-${flow.isLocal}`}>
              <th scope="row">
                {flow.destinationCountyName}

                {flow.isLocal ? (
                  <span className="local-label">Local</span>
                ) : null}
              </th>

              <td className="numeric-column">
                {formatInteger(flow.placementCount)}
              </td>

              <td className="numeric-column">
                {formatPercentage(flow.placementShare)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
