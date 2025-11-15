import type { AppTab } from '../store/AppStateContext';

export const TABS: Array<{ id: AppTab; label: string }> = [
  { id: 'today', label: 'Главная' },
  { id: 'calendar', label: 'Календарь' },
  { id: 'goals', label: 'Цели' },
  { id: 'leaderboard', label: 'Статистика' }
];

export const TAB_LABELS = TABS.reduce<Record<AppTab, string>>((acc, tab) => {
  acc[tab.id] = tab.label;
  return acc;
}, {} as Record<AppTab, string>);
