import { defineConfig } from "vite";

export default defineConfig({
  base: "/flipbook-maker/",
  build: {
    outDir: "dist",
    target: "es2020",
  },
});
