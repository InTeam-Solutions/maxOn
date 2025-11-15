import type { ReactNode } from 'react';
import styles from './SectionHeading.module.css';

interface SectionHeadingProps {
  title: string;
  subtitle?: string;
  actionSlot?: ReactNode;
}

export const SectionHeading = ({ title, subtitle, actionSlot }: SectionHeadingProps) => (
  <div className={styles.wrapper}>
    <div>
      <div className={styles.title}>{title}</div>
      {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
    </div>
    {actionSlot && <div className={styles.action}>{actionSlot}</div>}
  </div>
);
