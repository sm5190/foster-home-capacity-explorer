import { describe, expect, it } from "vitest";

import {
  buildCountyListHref,
  getNextSortDirection,
  parseCountyListSearchParams,
} from "../../lib/county-query";

describe("county query helpers", () => {
  it("returns default query values", () => {
    const result = parseCountyListSearchParams({});

    expect(result).toEqual({
      invalidQuery: false,
      query: {
        focus: "recruitment",
        age: "all",
        search: "",
        sort: "priority",
        direction: "desc",
      },
    });
  });

  it("parses valid URL values", () => {
    const result = parseCountyListSearchParams({
      focus: "engagement",
      age: "13-17",
      search: "Cook",
      sort: "homesWithoutRecentActivity",
      direction: "asc",
    });

    expect(result.invalidQuery).toBe(false);

    expect(result.query).toEqual({
      focus: "engagement",
      age: "13-17",
      search: "Cook",
      sort: "homesWithoutRecentActivity",
      direction: "asc",
    });
  });

  it("restores defaults for invalid values", () => {
    const result = parseCountyListSearchParams({
      focus: "retention",
    });

    expect(result.invalidQuery).toBe(true);

    expect(result.query.focus).toBe("recruitment");
  });

  it("uses the first repeated parameter", () => {
    const result = parseCountyListSearchParams({
      focus: ["engagement", "recruitment"],
    });

    expect(result.query.focus).toBe("engagement");
  });

  it("builds a shareable query URL", () => {
    const href = buildCountyListHref({
      focus: "recruitment",
      age: "6-12",
      search: "Cook",
      sort: "county",
      direction: "asc",
    });

    const url = new URL(href, "http://localhost");

    expect(url.searchParams.get("focus")).toBe("recruitment");

    expect(url.searchParams.get("age")).toBe("6-12");

    expect(url.searchParams.get("search")).toBe("Cook");

    expect(url.searchParams.get("sort")).toBe("county");

    expect(url.searchParams.get("direction")).toBe("asc");
  });

  it("toggles an active descending sort to ascending", () => {
    expect(
      getNextSortDirection(
        {
          focus: "recruitment",
          age: "all",
          search: "",
          sort: "county",
          direction: "desc",
        },
        "county",
      ),
    ).toBe("asc");
  });

  it("starts a newly selected sort in descending order", () => {
    expect(
      getNextSortDirection(
        {
          focus: "recruitment",
          age: "all",
          search: "",
          sort: "priority",
          direction: "desc",
        },
        "childrenCurrentlyInCare",
      ),
    ).toBe("desc");
  });
});
