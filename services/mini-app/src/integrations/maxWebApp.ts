import type { MaxWebApp } from '../types/maxWebApp';

const DEFAULT_SRC = 'https://static.maxhub.com/sdk/max-web-app.js';
let loader: Promise<MaxWebApp | undefined> | null = null;

const injectScript = (src: string) =>
  new Promise<MaxWebApp | undefined>((resolve, reject) => {
    if (document.querySelector(`script[data-max-web-app]`)) {
      resolve(window.MaxWebApp);
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.dataset.maxWebApp = 'true';
    script.onload = () => resolve(window.MaxWebApp);
    script.onerror = () => reject(new Error('max-web-app.js failed to load'));
    document.head.appendChild(script);
  });

export const ensureMaxWebApp = () => {
  if (window.MaxWebApp) {
    return Promise.resolve(window.MaxWebApp);
  }

  if (!loader) {
    const src = import.meta.env.VITE_MAX_WEB_APP_SRC ?? DEFAULT_SRC;
    loader = injectScript(src).catch((error) => {
      console.warn(error);
      return undefined;
    });
  }

  return loader;
};

