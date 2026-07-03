import { defineConfig } from "vite";

export default defineConfig({
  // Relative base so the build works both at the project-pages path
  // (luan-vp.github.io/flipbook-maker/) and at the custom subdomain root
  // (flipbook.luanvp.info/).
  base: "./",
  build: {
    outDir: "dist",
    target: "es2020",
  },
});
