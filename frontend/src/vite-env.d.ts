/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** Default on. Set to "false" to disable. */
  readonly VITE_ENABLE_POWERSYNC?: string;
  /** Dev sync console logs. Default on in dev; set "true" to force in prod build. */
  readonly VITE_SYNC_DEBUG?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
