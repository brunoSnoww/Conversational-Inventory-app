/** Fixed ngrok dev domain — must match ngrok.yml + ./scripts/ngrok-all.sh */
const VERCEL_NGROK_FALLBACK = 'https://canine-scrambled-reseller.ngrok-free.dev';

/** API origin for fetch + PowerSync sync/token (no trailing slash). */
export function getApiBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_API_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, '');
  }

  // Vercel builds without VITE_API_URL bake in localhost — phones cannot reach that.
  if (import.meta.env.PROD && typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'kaizntree-app.vercel.app' || host.endsWith('.vercel.app')) {
      return VERCEL_NGROK_FALLBACK;
    }
  }

  return 'http://localhost:8000';
}
