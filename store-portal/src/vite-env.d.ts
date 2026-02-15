/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_STORE_API_BASE_URL?: string
  readonly VITE_STORE_PORTAL_DEMO_AUTO_LOGIN?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
