import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const serverOnlyStub = fileURLToPath(
  new URL("./tests/helpers/server-only.ts", import.meta.url),
);

export default defineConfig({
  resolve: {
    alias: {
      "server-only": serverOnlyStub,
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    clearMocks: true,
    restoreMocks: true,
  },
});
