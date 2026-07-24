import "server-only";

import { randomUUID } from "node:crypto";

import { RuntimeDatabaseError } from "./db";
import { RepositoryDataError } from "./repositories/errors";
import { apiErrorResponseSchema, type ApiErrorCode } from "./schemas";
import { CountyNotFoundError } from "./services/errors";

export type ApiRequestContext = {
  requestId: string;
  route: string;
  method: string;
  startedAt: number;
};

type ApiResponseOptions = {
  status: number;
  cacheControl?: string;
  error?: unknown;
};

/**
 * Create request metadata used for response headers and logs.
 */
export function createApiRequestContext(
  request: Request,
  route: string,
): ApiRequestContext {
  return {
    requestId: randomUUID(),
    route,
    method: request.method,
    startedAt: Date.now(),
  };
}

function writeRequestLog(
  context: ApiRequestContext,
  status: number,
  error?: unknown,
): void {
  const logEntry = {
    event: "api_request",
    requestId: context.requestId,
    route: context.route,
    method: context.method,
    status,
    durationMs: Date.now() - context.startedAt,
    errorName: error instanceof Error ? error.name : undefined,
  };

  const serializedEntry = JSON.stringify(logEntry);

  if (status >= 500) {
    console.error(serializedEntry);
    return;
  }

  if (status >= 400) {
    console.warn(serializedEntry);
    return;
  }

  console.info(serializedEntry);
}

/**
 * Return a JSON response with standard API headers.
 */
export function createApiJsonResponse<T>(
  body: T,
  context: ApiRequestContext,
  options: ApiResponseOptions,
): Response {
  writeRequestLog(context, options.status, options.error);

  return Response.json(body, {
    status: options.status,
    headers: {
      "Cache-Control": options.cacheControl ?? "no-store",
      "X-Request-ID": context.requestId,
    },
  });
}

/**
 * Return the stable public API error envelope.
 */
export function createApiErrorResponse(
  code: ApiErrorCode,
  message: string,
  status: number,
  context: ApiRequestContext,
  error?: unknown,
): Response {
  const body = apiErrorResponseSchema.parse({
    error: {
      code,
      message,
    },
    requestId: context.requestId,
  });

  return createApiJsonResponse(body, context, {
    status,
    error,
  });
}

/**
 * Convert expected service and database failures into public responses.
 *
 * Internal error messages, paths, SQL, and stack traces are never returned.
 */
export function handleApiError(
  error: unknown,
  context: ApiRequestContext,
): Response {
  if (error instanceof CountyNotFoundError) {
    return createApiErrorResponse(
      "COUNTY_NOT_FOUND",
      "The requested county was not found.",
      404,
      context,
      error,
    );
  }

  if (
    error instanceof RuntimeDatabaseError ||
    error instanceof RepositoryDataError
  ) {
    return createApiErrorResponse(
      "DATABASE_UNAVAILABLE",
      "The aggregate data is temporarily unavailable.",
      503,
      context,
      error,
    );
  }

  return createApiErrorResponse(
    "INTERNAL_ERROR",
    "An unexpected server error occurred.",
    500,
    context,
    error,
  );
}
