import widgetCss from './widget-bundle.css?inline';
import { mountWidget, type WidgetInitConfig } from './widget';

function readBootScriptBase(): string {
  const sc = document.currentScript as HTMLScriptElement | null;
  if (sc?.src) {
    return new URL('.', sc.src).href.replace(/\/$/, '');
  }
  const scripts = document.getElementsByTagName('script');
  for (let i = scripts.length - 1; i >= 0; i--) {
    const src = scripts[i].src;
    if (src && /\/widget\.js(\?|$)/.test(src)) {
      return new URL('.', src).href.replace(/\/$/, '');
    }
  }
  return '';
}

const bootScriptBase = readBootScriptBase();

export default {
  init(config: WidgetInitConfig) {
    const scriptBase = (config.scriptBaseUrl ?? bootScriptBase).replace(/\/$/, '');
    mountWidget({ ...config, scriptBaseUrl: scriptBase }, widgetCss);
  },
};
