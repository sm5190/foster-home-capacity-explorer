import {
  countyListQuerySchema,
  type CountyListQuery,
  type CountySort,
  type SortDirection,
} from "./schemas";

export type RawSearchParams = Record<string, string | string[] | undefined>;

type ParsedCountyQuery = {
  query: CountyListQuery;
  invalidQuery: boolean;
};

const COUNTY_QUERY_KEYS = [
  "focus",
  "age",
  "search",
  "sort",
  "direction",
] as const;

function getSingleValue(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) {
    return value[0];
  }

  return value;
}

export function parseCountyListSearchParams(
  searchParams: RawSearchParams,
): ParsedCountyQuery {
  const input: Record<string, string> = {};

  for (const key of COUNTY_QUERY_KEYS) {
    const value = getSingleValue(searchParams[key]);

    if (value !== undefined) {
      input[key] = value;
    }
  }

  const result = countyListQuerySchema.safeParse(input);

  if (result.success) {
    return {
      query: result.data,
      invalidQuery: false,
    };
  }

  return {
    query: countyListQuerySchema.parse({}),
    invalidQuery: true,
  };
}

export function buildCountyListHref(
  query: CountyListQuery,
  overrides: Partial<CountyListQuery> = {},
): string {
  const nextQuery: CountyListQuery = {
    ...query,
    ...overrides,
  };

  const parameters = new URLSearchParams();

  parameters.set("focus", nextQuery.focus);

  parameters.set("age", nextQuery.age);

  if (nextQuery.search.trim()) {
    parameters.set("search", nextQuery.search.trim());
  }

  parameters.set("sort", nextQuery.sort);

  parameters.set("direction", nextQuery.direction);

  return `/?${parameters.toString()}`;
}

export function getNextSortDirection(
  query: CountyListQuery,
  sort: CountySort,
): SortDirection {
  if (query.sort === sort && query.direction === "desc") {
    return "asc";
  }

  return "desc";
}
