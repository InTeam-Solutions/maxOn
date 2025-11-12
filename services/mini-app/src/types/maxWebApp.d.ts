export interface MaxWebAppUser {
  id: string;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  avatar_url?: string;
}

export interface MaxWebAppInitData {
  query_id?: string;
  user?: MaxWebAppUser;
  auth_date?: string;
  hash?: string;
  [key: string]: unknown;
}

export interface MaxWebApp {
  initDataUnsafe?: MaxWebAppInitData;
  ready: () => void;
  expand: () => void;
  close: () => void;
  onEvent?: (event: string, handler: (...args: unknown[]) => void) => void;
}

declare global {
  interface Window {
    MaxWebApp?: MaxWebApp;
  }
}

export {};

