import { afterAll, describe, expect, it } from "vitest";

import { GET as getCounties } from "../../app/api/counties/route";
import { GET as getCounty } from "../../app/api/counties/[countySlug]/route";
import { GET as getHealth } from "../../app/api/health/route";
import { closeDatabaseConnection } from "../../lib/db";
import {
  apiErrorResponseSchema,
  countyDetailResponseSchema,
  countyListResponseSchema,
  healthResponseSchema,
} from "../../lib/schemas";

describe("API route handlers", () => {
  afterAll(() => {
    closeDatabaseConnection();
  });

  it("returns real application health metadata", async () => {
    const response = getHealth(new Request("http://localhost/api/health"));

    expect(response.status).toBe(200);
    expect(response.headers.get("x-request-id")).toBeTruthy();

    const body = healthResponseSchema.parse(await response.json());

    expect(body).toEqual({
      status: "ok",
      service: "foster-home-capacity-explorer",
      schemaVersion: "1.3",
      dataCutoff: "2026-07-01",
      observationStart: "2022-01-01",
      buildStatus: "complete",
      appVersion: "0.1.0",
      commitSha: null,
    });
  });

  it("returns all counties with default query values", async () => {
    const response = getCounties(new Request("http://localhost/api/counties"));

    expect(response.status).toBe(200);

    const body = countyListResponseSchema.parse(await response.json());

    expect(body.query).toEqual({
      focus: "recruitment",
      age: "all",
      search: "",
      sort: "priority",
      direction: "desc",
    });

    expect(body.counties).toHaveLength(102);

    expect(body.totalCount).toBe(102);
  });

  it("filters counties using validated query parameters", async () => {
    const response = getCounties(
      new Request("http://localhost/api/counties?search=Cook"),
    );

    expect(response.status).toBe(200);

    const body = countyListResponseSchema.parse(await response.json());

    expect(body.counties.some((county) => county.countySlug === "cook")).toBe(
      true,
    );

    for (const county of body.counties) {
      expect(county.countyName.toLowerCase().includes("cook")).toBe(true);
    }
  });

  it("supports engagement sorting", async () => {
    const response = getCounties(
      new Request(
        "http://localhost/api/counties" +
          "?focus=engagement" +
          "&sort=priority" +
          "&direction=desc",
      ),
    );

    expect(response.status).toBe(200);

    const body = countyListResponseSchema.parse(await response.json());

    expect(body.query.focus).toBe("engagement");

    expect(body.totalCount).toBe(102);
  });

  it("rejects invalid county query values", async () => {
    const response = getCounties(
      new Request("http://localhost/api/counties?focus=retention"),
    );

    expect(response.status).toBe(400);

    const body = apiErrorResponseSchema.parse(await response.json());

    expect(body.error).toEqual({
      code: "INVALID_QUERY",
      message: "One or more county query parameters are invalid.",
    });

    expect(response.headers.get("x-request-id")).toBe(body.requestId);
  });

  it("rejects unknown query parameters", async () => {
    const response = getCounties(
      new Request("http://localhost/api/counties?unknown=value"),
    );

    expect(response.status).toBe(400);

    const body = apiErrorResponseSchema.parse(await response.json());

    expect(body.error.code).toBe("INVALID_QUERY");
  });

  it("returns a complete county capacity brief", async () => {
    const response = await getCounty(
      new Request("http://localhost/api/counties/cook"),
      {
        params: Promise.resolve({
          countySlug: "cook",
        }),
      },
    );

    expect(response.status).toBe(200);

    const body = countyDetailResponseSchema.parse(await response.json());

    expect(body.county).toMatchObject({
      countySlug: "cook",
      countyName: "Cook",
      childrenCurrentlyInCare: 1_933,
      currentFosterPlacements: 1_044,
    });

    expect(
      body.placementSettings.kin.count +
        body.placementSettings.fosterHome.count +
        body.placementSettings.nonfamily.count,
    ).toBe(body.placementSettings.totalCurrentPlacements);
  });

  it("returns 404 for an unknown county", async () => {
    const response = await getCounty(
      new Request("http://localhost/api/counties/not-a-real-county"),
      {
        params: Promise.resolve({
          countySlug: "not-a-real-county",
        }),
      },
    );

    expect(response.status).toBe(404);

    const body = apiErrorResponseSchema.parse(await response.json());

    expect(body.error).toEqual({
      code: "COUNTY_NOT_FOUND",
      message: "The requested county was not found.",
    });

    expect(response.headers.get("x-request-id")).toBe(body.requestId);
  });

  it("returns 400 for an invalid county slug", async () => {
    const response = await getCounty(
      new Request("http://localhost/api/counties/invalid"),
      {
        params: Promise.resolve({
          countySlug: "../database",
        }),
      },
    );

    expect(response.status).toBe(400);

    const body = apiErrorResponseSchema.parse(await response.json());

    expect(body.error.code).toBe("INVALID_QUERY");
  });
});
