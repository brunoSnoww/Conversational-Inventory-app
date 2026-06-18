const NGROK_SUFFIXES = ['ngrok-free.app', 'ngrok-free.dev'] as const;

export function isNgrokHost(hostOrUrl: string): boolean {
  try {
    const host = hostOrUrl.includes('://') ? new URL(hostOrUrl).hostname : hostOrUrl;
    return NGROK_SUFFIXES.some((suffix) => host.endsWith(suffix));
  } catch {
    return NGROK_SUFFIXES.some((suffix) => hostOrUrl.includes(suffix));
  }
}

export function ngrokSkipHeaders(hostOrUrl?: string): Record<string, string> {
  if (hostOrUrl && isNgrokHost(hostOrUrl)) {
    return { 'ngrok-skip-browser-warning': 'true' };
  }
  return {};
}
