import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AgeAlignmentTable } from "../../../components/age-alignment-table";
import { CountyActions } from "../../../components/county-actions";
import { EngagementPanel } from "../../../components/engagement-panel";
import { MetricCard } from "../../../components/metric-card";
import { OpportunityBadge } from "../../../components/opportunity-badge";
import { PlacementFlowTable } from "../../../components/placement-flow-table";
import { PlacementSettings } from "../../../components/placement-settings";
import {
  formatDecimal,
  formatInteger,
  formatPercentage,
} from "../../../lib/formatters";
import {
  CountyNotFoundError,
  createCapacityService,
} from "../../../lib/services";

import { CapacityTrendChart } from "../../../components/capacity-trend-chart";

type CountyPageProps = {
  params: Promise<{
    countySlug: string;
  }>;
};

function getCountyBriefOrNotFound(countySlug: string) {
  const service = createCapacityService();

  try {
    return service.getCountyCapacityBrief(countySlug);
  } catch (error) {
    if (error instanceof CountyNotFoundError) {
      notFound();
    }

    throw error;
  }
}

export async function generateMetadata({
  params,
}: CountyPageProps): Promise<Metadata> {
  const { countySlug } = await params;

  try {
    const service = createCapacityService();

    const brief = service.getCountyCapacityBrief(countySlug);

    return {
      title: `${brief.county.countyName} County Capacity Brief`,
      description:
        "Recruitment and existing-home " +
        "engagement indicators for " +
        `${brief.county.countyName} County.`,
    };
  } catch {
    return {
      title: "County not found",
    };
  }
}

export default async function CountyPage({ params }: CountyPageProps) {
  const { countySlug } = await params;

  const brief = getCountyBriefOrNotFound(countySlug);

  const { county } = brief;

  return (
    <div className="page-shell">
      <nav aria-label="Breadcrumb" className="breadcrumb">
        <Link href="/">Statewide priorities</Link>

        <span aria-hidden="true">/</span>

        <span aria-current="page">{county.countyName}</span>
      </nav>

      <section className="hero hero--county">
        <div>
          <p className="eyebrow">County Capacity Brief</p>

          <h1>{county.countyName} County</h1>

          <p className="hero__description">{brief.diagnosis}</p>
        </div>

        <div className="hero__aside">
          <div className="data-date">Data as of July 1, 2026</div>

          <CountyActions />
        </div>
      </section>

      <section aria-labelledby="county-diagnosis" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Diagnosis</p>

            <h2 id="county-diagnosis">What stands out</h2>
          </div>
        </div>

        <div className="opportunity-grid">
          <article className="opportunity-panel">
            <OpportunityBadge
              focus="recruitment"
              level={county.recruitment.level}
            />

            <h3>Recruitment</h3>

            {county.recruitment.reasons.length > 0 ? (
              <ul className="evidence-list">
                {county.recruitment.reasons.map((reason) => (
                  <li key={reason.code}>{reason.label}</li>
                ))}
              </ul>
            ) : (
              <p>No statewide recruitment threshold was met.</p>
            )}
          </article>

          <article className="opportunity-panel">
            <OpportunityBadge
              focus="engagement"
              level={county.engagement.level}
            />

            <h3>Existing-home engagement</h3>

            {county.engagement.reasons.length > 0 ? (
              <ul className="evidence-list">
                {county.engagement.reasons.map((reason) => (
                  <li key={reason.code}>{reason.label}</li>
                ))}
              </ul>
            ) : (
              <p>No statewide engagement threshold was met.</p>
            )}
          </article>
        </div>
      </section>

      <section
        aria-labelledby="recruitment-snapshot"
        className="content-section"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Recruitment snapshot</p>

            <h2 id="recruitment-snapshot">Current county context</h2>
          </div>
        </div>

        <div className="metric-grid">
          <MetricCard
            label="Children currently in care"
            value={formatInteger(county.childrenCurrentlyInCare)}
          />

          <MetricCard
            label="Currently licensed foster homes"
            value={formatInteger(county.currentFosterHomes)}
          />

          <MetricCard
            detail={"Pressure indicator, not a " + "bed-capacity calculation"}
            label="Children per current home"
            value={formatDecimal(county.childrenPerCurrentHome, 1)}
          />

          <MetricCard
            detail={`${formatInteger(
              county.localFosterPlacements,
            )} of ${formatInteger(
              county.currentFosterPlacements,
            )} current foster-home placements`}
            label="Placed in the removal county"
            value={formatPercentage(county.localPlacementRate)}
          />
        </div>
      </section>

      <section
        className="content-section"
        aria-labelledby="capacity-pressure-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Capacity pressure over time</p>

            <h2 id="capacity-pressure-heading">Is county pressure changing?</h2>

            <p>
              Monthly children-per-home snapshots from July 2025 through July
              2026.
            </p>
          </div>
        </div>

        <CapacityTrendChart
          countyName={county.countyName}
          points={brief.capacityTrend}
          summary={brief.capacityTrendSummary}
        />
      </section>

      <section aria-labelledby="placement-settings" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Current placement settings</p>

            <h2 id="placement-settings">Where children are placed</h2>

            <p>
              Counts reconcile to{" "}
              {formatInteger(brief.placementSettings.totalCurrentPlacements)}{" "}
              children currently in care.
            </p>
          </div>
        </div>

        <PlacementSettings placementSettings={brief.placementSettings} />
      </section>

      <section aria-labelledby="placement-flow" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Cross-county placement flow</p>

            <h2 id="placement-flow">Foster-home placement destinations</h2>

            <p>
              Top destination counties for current foster-home placements
              originating in {county.countyName}.
            </p>
          </div>
        </div>

        <PlacementFlowTable flows={brief.placementFlows} />
      </section>

      <section aria-labelledby="age-alignment" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Current age-preference alignment</p>

            <h2 id="age-alignment">
              Children and current provider preferences
            </h2>
          </div>
        </div>

        <AgeAlignmentTable rows={brief.ageAlignment} />
      </section>

      <section aria-labelledby="engagement" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Existing-home engagement</p>

            <h2 id="engagement">Current provider activity</h2>
          </div>
        </div>

        <EngagementPanel county={county} />
      </section>

      <section aria-labelledby="questions" className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Questions for local review</p>
            <h2>What should staff explore next?</h2>
          </div>
        </div>

        <ol className="question-list">
          {brief.investigationQuestions.map((question) => (
            <li key={question.displayOrder}>{question.questionText}</li>
          ))}
        </ol>
      </section>
    </div>
  );
}
