import { MaxUI } from '@maxhub/max-ui';
import { useEffect, type ReactNode } from 'react';
import { AppStateProvider, useAppState } from '../store/AppStateContext';
import { ChatProvider } from '../store/ChatContext';
import { ensureMaxWebApp } from '../integrations/maxWebApp';
import { apiClient } from '../services/api';

const MaxAppInitGate = ({ children }: { children: ReactNode }) => {
  const { setInitData } = useAppState();

  useEffect(() => {
    let mounted = true;

    const initializeUser = () => {
      if (!mounted) return;

      console.log('[MaxOn] 🚀 Initializing user authentication...');
      console.log('[MaxOn] 🔍 window.WebApp exists:', !!window.WebApp);
      console.log('[MaxOn] 🔍 window.MaxWebApp exists:', !!window.MaxWebApp);
      console.log('[MaxOn] 🔍 window.Telegram exists:', !!(window as any).Telegram);
      console.log('[MaxOn] 🔍 All window keys:', Object.keys(window).filter(k =>
        k.toLowerCase().includes('max') ||
        k.toLowerCase().includes('telegram') ||
        k.toLowerCase().includes('webapp') ||
        k.toLowerCase().includes('init')
      ));

      // Check URL parameters for initData (Telegram-style)
      const urlParams = new URLSearchParams(window.location.search);
      const initDataRaw = urlParams.get('tgWebAppData') || urlParams.get('initData');
      console.log('[MaxOn] 🔍 URL initData:', initDataRaw ? 'present' : 'not found');
      console.log('[MaxOn] 🔍 All URL params:', Array.from(urlParams.keys()));

      // Try to parse initData from URL if present
      if (initDataRaw) {
        try {
          const params = new URLSearchParams(initDataRaw);
          const userJson = params.get('user');
          if (userJson) {
            const user = JSON.parse(decodeURIComponent(userJson));
            console.log('[MaxOn] ✅ Found user in URL initData:', user);
            if (user.id) {
              apiClient.configure({ userId: String(user.id) });
              console.log('[MaxOn] ✅ API client configured with user_id from URL initData:', user.id);
              setInitData({ user });
              return;
            }
          }
        } catch (e) {
          console.error('[MaxOn] ❌ Failed to parse initData:', e);
        }
      }

      // Priority 1: Check if WebApp is already available (injected by MAX messenger)
      const webApp = window.WebApp || window.MaxWebApp;
      if (webApp) {
        console.log('[MaxOn] 🔍 Found window.WebApp:', webApp);
        console.log('[MaxOn] 🔍 initDataUnsafe:', webApp.initDataUnsafe);
        console.log('[MaxOn] 🔍 initData:', webApp.initData);
        console.log('[MaxOn] 🔍 platform:', webApp.platform);
        console.log('[MaxOn] 🔍 version:', webApp.version);

        webApp.ready?.();
        const initData = webApp.initDataUnsafe ?? null;
        setInitData(initData);

        if (initData?.user?.id) {
          apiClient.configure({ userId: String(initData.user.id) });
          console.log('[MaxOn] ✅ API client configured with user_id from MAX WebApp:', initData.user.id);
          return;
        } else {
          console.log('[MaxOn] ⚠️ WebApp found but no user data in initDataUnsafe');
        }
      } else {
        console.log('[MaxOn] ⚠️ window.WebApp not found (not inside MAX messenger?)');
      }

      // Priority 2: Try URL parameter (for testing/development)
      const userIdFromUrl = urlParams.get('user_id');

      if (userIdFromUrl) {
        apiClient.configure({ userId: userIdFromUrl });
        console.log('[MaxOn] ⚠️ API client configured with user_id from URL:', userIdFromUrl);
        return;
      }

      // Priority 3: Try loading SDK script (if not already available)
      console.log('[MaxOn] 🔄 Attempting to load MAX WebApp SDK...');
      ensureMaxWebApp()
        .then((sdk) => {
          if (!mounted) return;

          sdk?.ready();
          const initData = sdk?.initDataUnsafe ?? null;
          setInitData(initData);

          if (initData?.user?.id) {
            apiClient.configure({ userId: String(initData.user.id) });
            console.log('[MaxOn] ✅ API client configured with user_id from loaded SDK:', initData.user.id);
            return;
          }

          // Last fallback - demo user
          const demoUserId = import.meta.env.VITE_DEMO_USER_ID || '89578356';
          apiClient.configure({ userId: demoUserId });
          console.log('[MaxOn] ⚠️ Using demo user_id:', demoUserId);
        })
        .catch((error) => {
          console.error('[MaxOn] ❌ Failed to load MAX WebApp SDK:', error);
          if (!mounted) return;

          setInitData(null);
          // Last resort - demo user
          const demoUserId = import.meta.env.VITE_DEMO_USER_ID || '89578356';
          apiClient.configure({ userId: demoUserId });
          console.log('[MaxOn] ⚠️ Using demo user_id (SDK failed):', demoUserId);
        });
    };

    // Wait a bit for MAX messenger to inject SDK
    setTimeout(initializeUser, 100);

    return () => {
      mounted = false;
    };
  }, [setInitData]);

  return <>{children}</>;
};

export const AppProviders = ({ children }: { children: ReactNode }) => (
  <AppStateProvider>
    <ChatProvider>
      <MaxUI className="maxui-root">
        <MaxAppInitGate>{children}</MaxAppInitGate>
      </MaxUI>
    </ChatProvider>
  </AppStateProvider>
);
