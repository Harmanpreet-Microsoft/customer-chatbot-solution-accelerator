function trimSlash(s: string) {
  return s.replace(/\/$/, '');
}

function runtimeStr(key: keyof NonNullable<Window['__RUNTIME_CONFIG__']>): string {
  if (typeof window === 'undefined') {
    return '';
  }
  const v = window.__RUNTIME_CONFIG__?.[key];
  return v != null ? String(v).trim() : '';
}

function widgetScriptBase(): string {
  if (typeof window !== 'undefined' && window.location.origin) {
    return trimSlash(window.location.origin);
  }
  return '';
}

export function embedChatWidget() {
  const base = widgetScriptBase();
  if (!base) {
    return;
  }
  if (document.getElementById('ccsa-chat-widget-script')) {
    return;
  }
  const script = document.createElement('script');
  script.id = 'ccsa-chat-widget-script';
  script.src = `${base}/widget.js`;
  script.async = true;
  script.addEventListener('error', () => {
    console.error(
      '[chat widget] Failed to load widget.js from',
      script.src,
      import.meta.env.DEV
        ? 'Build the widget: cd chat-app/frontend && npm run build'
        : 'Redeploy scenario-frontend from repo root (see scenario-app/frontend/Dockerfile).',
    );
  });
  script.addEventListener('load', () => {
    const apiBase =
      runtimeStr('VITE_CHAT_API_BASE_URL') ||
      String(import.meta.env.VITE_CHAT_API_BASE_URL ?? '').trim() ||
      'http://localhost:8000';
    const themeRaw =
      (runtimeStr('VITE_CHAT_WIDGET_THEME') ||
        String(import.meta.env.VITE_CHAT_WIDGET_THEME ?? '').trim()).toLowerCase();
    const theme = themeRaw === 'light' || themeRaw === 'dark' ? themeRaw : undefined;
    const w = window.ChatWidget as { init?: (c: unknown) => void; default?: { init?: (c: unknown) => void } } | undefined;
    const init = w?.init ?? w?.default?.init;
    if (!init) {
      console.error('[chat widget] ChatWidget.init missing after load');
      return;
    }
    init({
      apiBaseUrl: trimSlash(apiBase),
      theme,
    });
  });
  document.body.appendChild(script);
}
