/// <reference types="vite/client" />

declare module '*?inline' {
  const content: string;
  export default content;
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface Window {
  __RUNTIME_CONFIG__?: {
    VITE_API_BASE_URL?: string;
  };
  ChatWidget?: {
    init: (config: { apiBaseUrl: string; theme?: 'light' | 'dark'; scriptBaseUrl?: string }) => void;
  };
}
