import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// The backend has no CORS middleware, so the browser cannot call it directly
// from another origin. In development, Vite forwards every request made to
// `<base>api/...` to the FastAPI server, which keeps the browser on a single
// origin and avoids CORS entirely.
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendUrl = env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
  const base = env.VITE_BASE_PATH || '/';
  const apiPrefix = `${base.replace(/\/$/, '')}/api`;

  const proxy = {
    [apiPrefix]: {
      target: backendUrl,
      changeOrigin: true,
      rewrite: (path) => path.replace(apiPrefix, '/api'),
    },
  };

  return {
    // The production build uses relative paths, so the same `dist/` folder
    // works at the site root and under an Onyxia /proxy/<port>/ sub-path.
    base: command === 'build' ? './' : base,
    plugins: [react()],
    server: { port: Number(env.VITE_PORT) || 5000, proxy },
    preview: { port: Number(env.VITE_PORT) || 4173, proxy },
  };
});