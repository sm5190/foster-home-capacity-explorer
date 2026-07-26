import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import Database from "better-sqlite3";
import { feature } from "topojson-client";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));

const projectRoot = path.resolve(currentDirectory, "..");

const atlasPath = path.join(
  projectRoot,
  "node_modules",
  "us-atlas",
  "counties-10m.json",
);

const databasePath = path.join(
  projectRoot,
  "data",
  "generated",
  "foster_capacity.db",
);

const outputPath = path.join(
  projectRoot,
  "lib",
  "map",
  "illinois-counties.json",
);

const ILLINOIS_STATE_FIPS = "17";
const EXPECTED_COUNTY_COUNT = 102;

function slugifyCounty(countyName) {
  return countyName
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function requireFile(filePath, description) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`${description} was not found: ${filePath}`);
  }
}

requireFile(atlasPath, "The us-atlas county topology");

requireFile(databasePath, "The generated aggregate database");

const topology = JSON.parse(fs.readFileSync(atlasPath, "utf8"));

const allCountyFeatures = feature(topology, topology.objects.counties);

if (allCountyFeatures.type !== "FeatureCollection") {
  throw new Error(
    "Expected the county topology to produce a FeatureCollection.",
  );
}

const illinoisFeatures = allCountyFeatures.features
  .filter((countyFeature) => {
    const fips = String(countyFeature.id).padStart(5, "0");

    return fips.startsWith(ILLINOIS_STATE_FIPS);
  })
  .map((countyFeature) => {
    const countyName = countyFeature.properties?.name;

    if (typeof countyName !== "string" || countyName.trim().length === 0) {
      throw new Error(`County ${countyFeature.id} is missing its name.`);
    }

    const fips = String(countyFeature.id).padStart(5, "0");

    return {
      ...countyFeature,
      id: fips,
      properties: {
        fips,
        countyName,
        countySlug: slugifyCounty(countyName),
      },
    };
  })
  .sort((first, second) => String(first.id).localeCompare(String(second.id)));

if (illinoisFeatures.length !== EXPECTED_COUNTY_COUNT) {
  throw new Error(
    "Unexpected Illinois map county count. " +
      `Expected ${EXPECTED_COUNTY_COUNT}; ` +
      `found ${illinoisFeatures.length}.`,
  );
}

const mapSlugs = new Set(
  illinoisFeatures.map((countyFeature) => countyFeature.properties.countySlug),
);

if (mapSlugs.size !== EXPECTED_COUNTY_COUNT) {
  throw new Error("Illinois geography produced duplicate county slugs.");
}

const database = new Database(databasePath, {
  readonly: true,
  fileMustExist: true,
});

const countyRows = database
  .prepare(
    `
      SELECT county_slug
      FROM county_summary
      ORDER BY county_slug
    `,
  )
  .all();

database.close();

const dataSlugs = new Set(countyRows.map((row) => row.county_slug));

const missingFromData = [...mapSlugs].filter(
  (countySlug) => !dataSlugs.has(countySlug),
);

const missingFromMap = [...dataSlugs].filter(
  (countySlug) => !mapSlugs.has(countySlug),
);

if (missingFromData.length > 0 || missingFromMap.length > 0) {
  throw new Error(
    [
      "County geography does not match the aggregate database.",
      `Missing from data: ${missingFromData.join(", ") || "none"}`,
      `Missing from map: ${missingFromMap.join(", ") || "none"}`,
    ].join("\n"),
  );
}

const output = {
  type: "FeatureCollection",
  features: illinoisFeatures,
};

fs.mkdirSync(path.dirname(outputPath), {
  recursive: true,
});

fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");

console.log(`Created Illinois county geography: ${outputPath}`);

console.log(`Illinois county features: ${illinoisFeatures.length}`);
