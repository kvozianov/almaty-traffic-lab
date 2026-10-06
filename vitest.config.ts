import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/lab/**/*.test.ts"],
    testTimeout: 30_000,
    hookTimeout: 60_000,
  },
});
