import clsx from 'clsx';
import type { AppTab } from '../store/AppStateContext';
import { TABS } from '../constants/tabs';
import styles from './TabStrip.module.css';

interface TabStripProps {
  activeTab: AppTab;
  onChange: (tab: AppTab) => void;
}

export const TabStrip = ({ activeTab, onChange }: TabStripProps) => (
  <nav className={styles.tabStrip} aria-label="Основная навигация">
    {TABS.map((tab) => (
      <button
        key={tab.id}
        type="button"
        className={clsx(styles.tab, activeTab === tab.id && styles.active)}
        onClick={() => onChange(tab.id)}
      >
        {tab.label}
      </button>
    ))}
  </nav>
);

