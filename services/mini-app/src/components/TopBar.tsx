import { IconButton, Typography } from '@maxhub/max-ui';
import { useAppState } from '../store/AppStateContext';
import { TAB_LABELS } from '../constants/tabs';
import { apiClient } from '../services/api';
import styles from './TopBar.module.css';

export const TopBar = () => {
  const { activeTab } = useAppState();
  const userId = apiClient.getUserId();

  return (
    <header className={styles.topBar}>
      <div className={styles.brand}>
        <div className={styles.logoContainer}>
          <img src="/logo.png" alt="maxOn" className={styles.logo} />
        </div>
      </div>
      {userId && (
        <div className={styles.debugBadge}>
          DEBUG: {userId}
        </div>
      )}
      <IconButton
        mode="tertiary"
        appearance="neutral"
        aria-label="Дополнительное меню"
        className={styles.iconButton}
      >
        ⋮
      </IconButton>
    </header>
  );
};
