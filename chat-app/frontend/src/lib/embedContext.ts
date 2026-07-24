let widgetScriptBaseUrl: string | null = null;
let useHostPageAuth = false;

export function setEmbedAuthBaseUrl(url: string | null) {
  widgetScriptBaseUrl = url ? url.replace(/\/$/, '') : null;
}

export function setUseHostPageAuth(enabled: boolean) {
  useHostPageAuth = enabled;
}

export function isWidgetEmbedded(): boolean {
  return useHostPageAuth;
}

export function resolveAuthOrigin(): string {
  if (typeof window === 'undefined') {
    return widgetScriptBaseUrl || '';
  }
  if (useHostPageAuth) {
    return window.location.origin.replace(/\/$/, '');
  }
  const host = window.location.origin.replace(/\/$/, '');
  if (widgetScriptBaseUrl && widgetScriptBaseUrl !== host) {
    return host;
  }
  return widgetScriptBaseUrl || host;
}

export function getEmbedAuthBaseUrl(): string | null {
  const origin = resolveAuthOrigin();
  return origin || null;
}
