import { IconButton, Typography } from '@maxhub/max-ui';
import { useAppState } from '../store/AppStateContext';
import { TAB_LABELS } from '../constants/tabs';
import styles from './TopBar.module.css';

export const TopBar = () => {
  const { activeTab } = useAppState();

  return (
    <header className={styles.topBar}>
      <div className={styles.brand}>
        <span className={styles.logoMark} />
        <div className={styles.brandText}>
          <Typography.Title variant="medium-strong">
            maxOn
          </Typography.Title>
          <Typography.Body variant="small" className={styles.sectionLabel}>
            · {TAB_LABELS[activeTab]}
          </Typography.Body>
        </div>
      </div>
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
