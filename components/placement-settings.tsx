import { formatInteger, formatPercentage } from "../lib/formatters";
import type { CountyPlacementSettings } from "../lib/schemas";

type PlacementSettingsProps = {
  placementSettings: CountyPlacementSettings;
};

export function PlacementSettings({
  placementSettings,
}: PlacementSettingsProps) {
  const rows = [
    {
      label: "Kin",
      value: placementSettings.kin,
    },
    {
      label: "Foster home",
      value: placementSettings.fosterHome,
    },
    {
      label: "Nonfamily",
      value: placementSettings.nonfamily,
    },
  ];

  return (
    <div className="breakdown-list">
      {rows.map((row) => {
        const width = row.value.share === null ? 0 : row.value.share * 100;

        return (
          <div className="breakdown-row" key={row.label}>
            <div className="breakdown-row__heading">
              <span>{row.label}</span>

              <span>
                {formatInteger(row.value.count)}
                {" · "}
                {formatPercentage(row.value.share)}
              </span>
            </div>

            <div aria-hidden="true" className="bar-track">
              <span
                className="bar-fill"
                style={{
                  width: `${width}%`,
                }}
              />
            </div>
          </div>
        );
      })}

      <p className="method-note">
        Nonfamily placements are included only to describe children&apos;s
        current placement settings. They are excluded from foster-home
        recruitment and engagement calculations.
      </p>
    </div>
  );
}
