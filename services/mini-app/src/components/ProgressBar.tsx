import clsx from 'clsx';
import styles from './ProgressBar.module.css';

interface ProgressBarProps {
  value: number;
  accent?: 'green' | 'blue' | 'violet';
  compact?: boolean;
}

const ACCENT_MAP = {
  green: 'var(--accent-green)',
  blue: 'var(--accent-blue)',
  violet: 'var(--accent-violet)'
} as const;

export const ProgressBar = ({ value, accent = 'green', compact }: ProgressBarProps) => {
  console.log('[ProgressBar] Rendering with value:', value, 'accent:', accent);
  return (
    <div className={clsx(styles.track, compact && styles.compact)}>
      <div
        className={styles.fill}
        style={{ width: `${value}%`, background: ACCENT_MAP[accent] }}
      />
    </div>
  );
};

