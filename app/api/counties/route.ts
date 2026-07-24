import {
  createApiErrorResponse,
  createApiJsonResponse,
  createApiRequestContext,
  handleApiError,
} from "../../../lib/api";
import { countyListQuerySchema } from "../../../lib/schemas";
import { createCapacityService } from "../../../lib/services";

export const runtime = "nodejs";

const ROUTE_NAME = "/api/counties";

/**
 * Convert URL query parameters into an object while retaining
 * unknown parameters so the strict Zod schema can reject them.
 */
function readQueryInput(request: Request): Record<string, string> {
  const requestUrl = new URL(request.url);

  return Object.fromEntries(requestUrl.searchParams.entries());
}

export function GET(request: Request): Response {
  const context = createApiRequestContext(request, ROUTE_NAME);

  const queryResult = countyListQuerySchema.safeParse(readQueryInput(request));

  if (!queryResult.success) {
    return createApiErrorResponse(
      "INVALID_QUERY",
      "One or more county query parameters are invalid.",
      400,
      context,
      queryResult.error,
    );
  }

  try {
    const service = createCapacityService();

    const body = service.getStatewidePriorities(queryResult.data);

    return createApiJsonResponse(body, context, {
      status: 200,
      cacheControl: "public, max-age=0, s-maxage=3600",
    });
  } catch (error) {
    return handleApiError(error, context);
  }
}
