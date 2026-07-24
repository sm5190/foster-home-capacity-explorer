import {
  createApiJsonResponse,
  createApiRequestContext,
  handleApiError,
} from "../../../lib/api";
import { APP_NAME, getAppVersion, getCommitSha } from "../../../lib/constants";
import { getDatabaseMetadata } from "../../../lib/db";
import { healthResponseSchema } from "../../../lib/schemas";

export const runtime = "nodejs";

const ROUTE_NAME = "/api/health";

export function GET(request: Request): Response {
  const context = createApiRequestContext(request, ROUTE_NAME);

  try {
    const metadata = getDatabaseMetadata();

    const body = healthResponseSchema.parse({
      status: "ok",
      service: APP_NAME,
      schemaVersion: metadata.schemaVersion,
      dataCutoff: metadata.reportingCutoff,
      observationStart: metadata.observationStart,
      buildStatus: metadata.buildStatus,
      appVersion: getAppVersion(),
      commitSha: getCommitSha(),
    });

    return createApiJsonResponse(body, context, {
      status: 200,
      cacheControl: "no-store",
    });
  } catch (error) {
    return handleApiError(error, context);
  }
}
