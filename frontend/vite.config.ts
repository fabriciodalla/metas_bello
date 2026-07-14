import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    // Bind mount do Docker Desktop no Windows (ainda mais dentro de pasta sincronizada pelo
    // OneDrive) não propaga eventos nativos de mudança de arquivo pro container — sem polling o
    // HMR nunca dispara, mesmo com o volume atualizado.
    watch: {
      usePolling: true,
      interval: 300,
    },
    proxy: {
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});
