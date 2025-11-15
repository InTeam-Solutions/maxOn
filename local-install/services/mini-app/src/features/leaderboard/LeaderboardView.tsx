import { Typography } from '@maxhub/max-ui';
import { leaderboardMock } from '../../mocks/data';
import styles from './LeaderboardView.module.css';

export const LeaderboardView = () => (
  <div className={styles.leaderboard}>
    <div className={styles.header}>
      <Typography.Title variant="medium-strong">
        Лидерборд
      </Typography.Title>
      <Typography.Body variant="small" className={styles.subtitle}>
        Поддерживай серию активных дней — maxOn cheering for you!
      </Typography.Body>
    </div>
    <div className="card">
      <ul className={styles.list}>
        {leaderboardMock.map((entry, index) => (
          <li key={entry.id} className={styles.row}>
            <div className={styles.left}>
              <span className={styles.rank}>{index + 1}</span>
              <span className={styles.avatar} style={{ background: entry.avatarColor }}>
                {entry.name[0]}
              </span>
              <div>
                <div className={styles.name}>{entry.name}</div>
                <div className={styles.username}>{entry.username}</div>
              </div>
            </div>
            <div className={styles.right}>
              <span className={styles.streak}>{entry.streakDays} дней</span>
              <span className={entry.delta >= 0 ? styles.positive : styles.negative}>
                {entry.delta > 0 ? `+${entry.delta}` : entry.delta}↑
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  </div>
);
