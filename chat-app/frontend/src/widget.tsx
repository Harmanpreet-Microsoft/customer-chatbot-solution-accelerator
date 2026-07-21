import { createRoot, type Root } from 'react-dom/client';
import { ErrorBoundary } from 'react-error-boundary';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { ErrorFallback } from '@/ErrorFallback';
import { AuthProvider } from '@/contexts/AuthContext';
import { setEmbedAuthBaseUrl, setUseHostPageAuth } from '@/lib/embedContext';
import { setWidgetApiBaseOverride } from '@/lib/api';
import { WidgetApp } from '@/WidgetApp.tsx';

export type WidgetInitConfig = {
  apiBaseUrl: string;
  theme?: 'light' | 'dark';
  scriptBaseUrl?: string;
};

let widgetRoot: Root | null = null;
let widgetHost: HTMLDivElement | null = null;

export function mountWidget(config: WidgetInitConfig, inlinedCss: string) {
  const apiBase = config.apiBaseUrl.trim().replace(/\/$/, '');
  const scriptBase = (config.scriptBaseUrl ?? '').trim().replace(/\/$/, '');
  setWidgetApiBaseOverride(apiBase);
  setEmbedAuthBaseUrl(scriptBase || null);
  setUseHostPageAuth(true);
  if (widgetRoot && widgetHost) {
    widgetRoot.unmount();
    widgetHost.remove();
    widgetRoot = null;
    widgetHost = null;
  }
  const mountHost = document.createElement('div');
  mountHost.id = 'ccsa-chat-widget-host';
  document.body.appendChild(mountHost);
  const shadow = mountHost.attachShadow({ mode: 'open' });
  const styleEl = document.createElement('style');
  styleEl.textContent = inlinedCss;
  shadow.appendChild(styleEl);
  const inner = document.createElement('div');
  shadow.appendChild(inner);
  widgetHost = mountHost;
  widgetRoot = createRoot(inner);
  const queryClient = new QueryClient();
  widgetRoot.render(
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <WidgetApp theme={config.theme} />
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>,
  );
}
