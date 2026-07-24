import {
  createApiErrorResponse,
  createApiJsonResponse,
  createApiRequestContext,
  handleApiError,
} from "../../../../lib/api";
import { countyRouteParamsSchema } from "../../../../lib/schemas";
import { createCapacityService } from "../../../../lib/services";

export const runtime = "nodejs";

const ROUTE_NAME = "/api/counties/[countySlug]";

type CountyRouteContext = {
  params: Promise<{
    countySlug: string;
  }>;
};

export async function GET(
  request: Request,
  routeContext: CountyRouteContext,
): Promise<Response> {
  const context = createApiRequestContext(request, ROUTE_NAME);

  const rawParams = await routeContext.params;

  const paramsResult = countyRouteParamsSchema.safeParse(rawParams);

  if (!paramsResult.success) {
    return createApiErrorResponse(
      "INVALID_QUERY",
      "The county identifier is invalid.",
      400,
      context,
      paramsResult.error,
    );
  }

  try {
    const service = createCapacityService();

    const body = service.getCountyCapacityBrief(paramsResult.data.countySlug);

    return createApiJsonResponse(body, context, {
      status: 200,
      cacheControl: "public, max-age=0, s-maxage=3600",
    });
  } catch (error) {
    return handleApiError(error, context);
  }
}
