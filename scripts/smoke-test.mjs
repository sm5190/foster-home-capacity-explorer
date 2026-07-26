const configuredBaseUrl = process.env.SMOKE_BASE_URL ?? "http://127.0.0.1:3000";

const baseUrl = configuredBaseUrl.replace(/\/+$/, "");

const pageChecks = [
  {
    path: "/",
    description: "statewide priorities page",
  },
  {
    path: "/county/cook",
    description: "Cook County brief",
  },
  {
    path: "/methodology",
    description: "methodology page",
  },
];

async function fetchWithTimeout(path) {
  const response = await fetch(`${baseUrl}${path}`, {
    redirect: "follow",
    signal: AbortSignal.timeout(15_000),
    headers: {
      "user-agent": "foster-insights-smoke-test",
    },
  });

  return response;
}

async function checkHealth() {
  const response = await fetchWithTimeout("/api/health");

  if (!response.ok) {
    throw new Error(`Health endpoint returned HTTP ${response.status}.`);
  }

  const body = await response.json();

  if (body.status !== "ok") {
    throw new Error(`Unexpected health status: ${String(body.status)}`);
  }

  if (body.dataCutoff !== "2026-07-01") {
    throw new Error("Health endpoint returned an unexpected data cutoff.");
  }

  if (body.schemaVersion !== "1.3") {
    throw new Error("Health endpoint returned an unexpected schema version.");
  }

  console.log("PASS /api/health", {
    status: body.status,
    schemaVersion: body.schemaVersion,
    dataCutoff: body.dataCutoff,
    buildStatus: body.buildStatus,
  });
}

async function checkPage({ path, description }) {
  const response = await fetchWithTimeout(path);

  if (!response.ok) {
    throw new Error(`${description} returned HTTP ${response.status}: ${path}`);
  }

  const body = await response.text();

  if (body.trim().length === 0) {
    throw new Error(`${description} returned an empty response: ${path}`);
  }

  console.log(`PASS ${path} (${description})`);
}

async function main() {
  console.log(`Running smoke tests against ${baseUrl}`);

  await checkHealth();

  for (const pageCheck of pageChecks) {
    await checkPage(pageCheck);
  }

  console.log("Production smoke tests passed.");
}

main().catch((error) => {
  console.error("Production smoke test failed.");

  console.error(error);

  process.exitCode = 1;
});
