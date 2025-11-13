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

    // Check URL parameters first
    const urlParams = new URLSearchParams(window.location.search);
    const userIdFromUrl = urlParams.get('user_id');

    if (userIdFromUrl) {
      // If user_id is in URL, use it directly
      apiClient.configure({ userId: userIdFromUrl });
      console.log('[MaxOn] API client configured with user_id from URL:', userIdFromUrl);
      setInitData(null); // No MAX WebApp SDK data
      return;
    }

    // Otherwise, try to initialize MAX WebApp SDK
    ensureMaxWebApp()
      .then((sdk) => {
        sdk?.ready();
        if (mounted) {
          const initData = sdk?.initDataUnsafe ?? null;
          setInitData(initData);

          // Configure API client with user_id from MAX WebApp
          if (initData?.user?.id) {
            apiClient.configure({
              userId: String(initData.user.id),
            });
            console.log('[MaxOn] API client configured with user_id:', initData.user.id);
          } else {
            // Fallback to demo user for development
            const demoUserId = import.meta.env.VITE_DEMO_USER_ID || '89578356';
            apiClient.configure({ userId: demoUserId });
            console.log('[MaxOn] Using demo user_id:', demoUserId);
          }
        }
      })
      .catch((error) => {
        console.error('[MaxOn] Failed to initialize MAX WebApp SDK:', error);
        if (mounted) {
          setInitData(null);
          // Fallback to demo user
          const demoUserId = import.meta.env.VITE_DEMO_USER_ID || '89578356';
          apiClient.configure({ userId: demoUserId });
          console.log('[MaxOn] Using demo user_id:', demoUserId);
        }
      });
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
