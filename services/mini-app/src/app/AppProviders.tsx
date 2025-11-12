import { MaxUI } from '@maxhub/max-ui';
import { useEffect, type ReactNode } from 'react';
import { AppStateProvider, useAppState } from '../store/AppStateContext';
import { ChatProvider } from '../store/ChatContext';
import { ensureMaxWebApp } from '../integrations/maxWebApp';

const MaxAppInitGate = ({ children }: { children: ReactNode }) => {
  const { setInitData } = useAppState();

  useEffect(() => {
    let mounted = true;
    ensureMaxWebApp()
      .then((sdk) => {
        sdk?.ready();
        if (mounted) {
          setInitData(sdk?.initDataUnsafe ?? null);
        }
      })
      .catch(() => {
        if (mounted) {
          setInitData(null);
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
