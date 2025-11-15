import { AppProviders } from './app/AppProviders';
import { AppShell } from './app/AppShell';

export const App = () => (
  <AppProviders>
    <AppShell />
  </AppProviders>
);

