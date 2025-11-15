import type { MaxWebApp } from '../types/maxWebApp';

const DEFAULT_SRC = 'https://st.max.ru/js/max-web-app.js';
let loader: Promise<MaxWebApp | undefined> | null = null;

const injectScript = (src: string) =>
  new Promise<MaxWebApp | undefined>((resolve, reject) => {
    if (document.querySelector(`script[data-max-web-app]`)) {
      resolve((window as any).WebApp);
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.dataset.maxWebApp = 'true';
    script.onload = () => resolve((window as any).WebApp);
    script.onerror = () => reject(new Error('max-web-app.js failed to load'));
    document.head.appendChild(script);
  });

export const ensureMaxWebApp = () => {
  // Check for window.WebApp (correct MAX Bridge object)
  if ((window as any).WebApp) {
    return Promise.resolve((window as any).WebApp);
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

