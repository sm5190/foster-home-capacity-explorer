export const metadata = {
  title: "About the Data",
};

export default function MethodologyPage() {
  return (
    <div className="page-shell page-shell--narrow">
      <section className="hero">
        <div>
          <p className="eyebrow">About the Data</p>

          <h1>How to interpret the Capacity Explorer</h1>

          <p className="hero__description">
            The application provides county-level analytical signals for
            discussion. The signals are not official DCFS classifications and do
            not establish why a placement or provider pattern occurred.
          </p>
        </div>

        <div className="data-date">Data as of July 1, 2026</div>
      </section>

      <section className="prose-section">
        <h2>Source datasets</h2>

        <p>
          The analysis uses child, placement, and corrected foster-home provider
          records covering January 1, 2022 through July 1, 2026.
        </p>

        <p>
          The public application contains only statewide and county-level
          aggregates. Child IDs, provider IDs, and individual placement
          histories are not included in the serving database.
        </p>

        <h2>Current children</h2>

        <p>
          A child is considered currently in care when the child record has no
          discharge date.
        </p>

        <h2>Currently licensed foster homes</h2>

        <p>
          A home is current when its license started on or before July 1, 2026
          and its license end date is on or after that date.
        </p>

        <h2>Children per currently licensed home</h2>

        <p>
          This divides current children associated with a removal county by
          currently licensed foster homes located in that county. It is a
          pressure indicator, not a measure of vacancies or licensed bed
          capacity.
        </p>

        <h2>Local placement rate</h2>

        <p>
          This is the share of current foster-home placements where the
          placement county matches the child&apos;s removal county. It includes
          both the percentage and the underlying numerator and denominator.
        </p>

        <h2>Provider preferences</h2>

        <p>
          Age-preference measures use providers&apos; current minimum and
          maximum preferred ages. Preferences do not indicate current
          availability or available beds.
        </p>

        <h2>Recent activity</h2>

        <p>
          A current home has recent activity when at least one foster-home
          placement overlaps the 90 days ending July 1, 2026.
        </p>

        <h2>Renewal dates</h2>

        <p>
          A renewal date is considered approaching when the license end date
          falls within the next 90 days. This does not mean a home is expected
          to close.
        </p>

        <h2>Nonfamily placement settings</h2>

        <p>
          Nonfamily placements remain in the child placement-setting breakdown.
          Nonfamily provider records are excluded from foster-home supply,
          preference, recruitment, activity, and engagement calculations.
        </p>

        <h2>Small-number guardrails</h2>

        <p>
          Percentages with small denominators are labeled Limited data. These
          records remain visible but do not receive strong priority labels
          solely because of unstable percentages.
        </p>

        <h2>Opportunity classifications</h2>

        <p>
          Recruitment and engagement labels are generated from transparent
          statewide percentile comparisons. They are analytical signals intended
          to support local investigation, not scores of county or provider
          performance.
        </p>
      </section>
    </div>
  );
}
