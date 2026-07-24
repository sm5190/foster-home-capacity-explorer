export const APP_NAME = "foster-home-capacity-explorer";

export const DEFAULT_DATABASE_PATH = "data/generated/foster_capacity.db";

export const EXPECTED_DATABASE_METADATA = {
  schemaVersion: "1.2",
  reportingCutoff: "2026-07-01",
  observationStart: "2022-01-01",
  buildStatus: "complete",
} as const;

/**
 * Resolve the deployed application version.
 *
 * The default matches package.json for local development.
 */
export function getAppVersion(): string {
  return process.env.APP_VERSION?.trim() || "0.1.0";
}

/**
 * Return the deployed source revision when one is provided.
 */
export function getCommitSha(): string | null {
  return process.env.APP_COMMIT_SHA?.trim() || null;
}
