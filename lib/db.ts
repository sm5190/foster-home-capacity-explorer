import "server-only";

import { existsSync, statSync } from "node:fs";
import path from "node:path";

import BetterSqlite3 from "better-sqlite3";

import { DEFAULT_DATABASE_PATH, EXPECTED_DATABASE_METADATA } from "./constants";

type SQLiteDatabase = InstanceType<typeof BetterSqlite3>;

type MetadataRow = {
  key: string;
  value: string;
};

export type RuntimeDatabaseMetadata = {
  schemaVersion: string;
  reportingCutoff: string;
  observationStart: string;
  buildStatus: string;
};

const REQUIRED_METADATA_KEYS = [
  "schema_version",
  "reporting_cutoff",
  "observation_start",
  "build_status",
] as const;

type DatabaseGlobal = typeof globalThis & {
  __fosterCapacityDatabase?: SQLiteDatabase;
};

const databaseGlobal = globalThis as DatabaseGlobal;

export class RuntimeDatabaseError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "RuntimeDatabaseError";
  }
}

/**
 * Resolve the configured database path relative to the repository root.
 *
 * Absolute paths are also supported for container deployments.
 */
export function getDatabasePath(): string {
  const configuredPath = process.env.FOSTER_DATABASE_PATH?.trim();
  const selectedPath = configuredPath || DEFAULT_DATABASE_PATH;

  return path.resolve(process.cwd(), selectedPath);
}

function validateDatabaseFile(databasePath: string): void {
  if (!existsSync(databasePath)) {
    throw new RuntimeDatabaseError(
      `Aggregate SQLite database was not found at: ${databasePath}`,
    );
  }

  if (!statSync(databasePath).isFile()) {
    throw new RuntimeDatabaseError(
      `Configured SQLite database path is not a file: ${databasePath}`,
    );
  }
}

function readMetadata(database: SQLiteDatabase): RuntimeDatabaseMetadata {
  const rows = database
    .prepare(
      `
        SELECT
          key,
          value
        FROM metadata
        WHERE key IN (?, ?, ?, ?)
      `,
    )
    .all(...REQUIRED_METADATA_KEYS) as MetadataRow[];

  const metadataByKey = new Map(rows.map((row) => [row.key, row.value]));

  const requireMetadataValue = (key: string): string => {
    const value = metadataByKey.get(key);

    if (!value) {
      throw new RuntimeDatabaseError(
        `Required database metadata is missing: ${key}`,
      );
    }

    return value;
  };

  return {
    schemaVersion: requireMetadataValue("schema_version"),
    reportingCutoff: requireMetadataValue("reporting_cutoff"),
    observationStart: requireMetadataValue("observation_start"),
    buildStatus: requireMetadataValue("build_status"),
  };
}

function validateMetadata(metadata: RuntimeDatabaseMetadata): void {
  const expected = EXPECTED_DATABASE_METADATA;

  if (metadata.schemaVersion !== expected.schemaVersion) {
    throw new RuntimeDatabaseError(
      `Unsupported database schema version. Expected ${expected.schemaVersion}, received ${metadata.schemaVersion}.`,
    );
  }

  if (metadata.reportingCutoff !== expected.reportingCutoff) {
    throw new RuntimeDatabaseError(
      `Unexpected reporting cutoff. Expected ${expected.reportingCutoff}, received ${metadata.reportingCutoff}.`,
    );
  }

  if (metadata.observationStart !== expected.observationStart) {
    throw new RuntimeDatabaseError(
      `Unexpected observation start. Expected ${expected.observationStart}, received ${metadata.observationStart}.`,
    );
  }

  if (metadata.buildStatus !== expected.buildStatus) {
    throw new RuntimeDatabaseError(
      `Database build is not complete. Received build status: ${metadata.buildStatus}.`,
    );
  }
}

function createDatabaseConnection(): SQLiteDatabase {
  const databasePath = getDatabasePath();

  validateDatabaseFile(databasePath);

  let database: SQLiteDatabase | undefined;

  try {
    database = new BetterSqlite3(databasePath, {
      readonly: true,
      fileMustExist: true,
      timeout: 5_000,
    });

    /*
     * readonly prevents opening the database for writes.
     * query_only adds a second SQLite-level protection against
     * accidental mutations through this connection.
     */
    database.pragma("query_only = ON");
    database.pragma("foreign_keys = ON");

    const metadata = readMetadata(database);
    validateMetadata(metadata);

    return database;
  } catch (error) {
    if (database?.open) {
      database.close();
    }

    if (error instanceof RuntimeDatabaseError) {
      throw error;
    }

    throw new RuntimeDatabaseError(
      `Unable to initialize the aggregate SQLite database at: ${databasePath}`,
      { cause: error },
    );
  }
}

/**
 * Return the shared read-only SQLite connection for this Node process.
 *
 * Storing it on globalThis prevents Next.js development hot reloads
 * from repeatedly opening new connections.
 */
export function getDatabase(): SQLiteDatabase {
  if (
    !databaseGlobal.__fosterCapacityDatabase ||
    !databaseGlobal.__fosterCapacityDatabase.open
  ) {
    databaseGlobal.__fosterCapacityDatabase = createDatabaseConnection();
  }

  return databaseGlobal.__fosterCapacityDatabase;
}

export function getDatabaseMetadata(): RuntimeDatabaseMetadata {
  const database = getDatabase();
  const metadata = readMetadata(database);

  validateMetadata(metadata);

  return metadata;
}

/**
 * Primarily used by integration tests to release the native connection.
 */
export function closeDatabaseConnection(): void {
  const database = databaseGlobal.__fosterCapacityDatabase;

  if (database?.open) {
    database.close();
  }

  databaseGlobal.__fosterCapacityDatabase = undefined;
}
