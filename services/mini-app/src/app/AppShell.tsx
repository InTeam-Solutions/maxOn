import { useMemo, useState, useEffect } from 'react';
import { Button } from '@maxhub/max-ui';
import { useAppState } from '../store/AppStateContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { TodayView } from '../features/today/TodayView';
import { CalendarView } from '../features/calendar/CalendarView';
import { GoalsView } from '../features/goals/GoalsView';
import { LeaderboardView } from '../features/leaderboard/LeaderboardView';
import { ChatPanel } from '../features/chat/ChatPanel';
import { TopBar } from '../components/TopBar';
import { TabStrip } from '../components/TabStrip';
import styles from './AppShell.module.css';

const TAB_COMPONENTS = {
  today: TodayView,
  calendar: CalendarView,
  goals: GoalsView,
  leaderboard: LeaderboardView
} as const;

export const AppShell = () => {
  const { activeTab, setActiveTab, isChatOpen, setChatOpen } = useAppState();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const ActiveComponent = useMemo(() => TAB_COMPONENTS[activeTab], [activeTab]);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [displayTab, setDisplayTab] = useState(activeTab);

  useEffect(() => {
    if (activeTab !== displayTab) {
      setIsTransitioning(true);
      const timer = setTimeout(() => {
        setDisplayTab(activeTab);
        setIsTransitioning(false);
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [activeTab, displayTab]);

  const CurrentComponent = TAB_COMPONENTS[displayTab];

  return (
    <div className={styles.appShell}>
      <div className={styles.surface}>
        <TopBar />
        <TabStrip activeTab={activeTab} onChange={setActiveTab} />
        <div className={styles.mainArea}>
          <section
            className={styles.contentColumn}
            style={{
              opacity: isTransitioning ? 0 : 1,
              transform: isTransitioning ? 'translateY(10px)' : 'translateY(0)',
              transition: 'opacity 200ms ease-out, transform 200ms ease-out'
            }}
          >
            <CurrentComponent />
          </section>
          {isDesktop ? (
            <aside className={styles.chatColumn}>
              <ChatPanel elevated />
            </aside>
          ) : (
            <div className={styles.mobileChatCta}>
              <Button
                mode="primary"
                appearance="themed"
                stretched
                className={styles.gradientButton}
                onClick={() => setChatOpen(true)}
              >
                Обсудить с maxOn
              </Button>
            </div>
          )}
        </div>
      </div>
      {!isDesktop && isChatOpen && (
        <div className={styles.mobileChatOverlay} onClick={() => setChatOpen(false)}>
          <div className={styles.chatSheet} onClick={(e) => e.stopPropagation()}>
            <div className={styles.chatSheetHeader}>
              <span style={{ fontSize: '16px', fontWeight: 700 }}>maxOn</span>
              <button className={styles.closeButton} onClick={() => setChatOpen(false)}>
                Закрыть
              </button>
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <ChatPanel onClose={() => setChatOpen(false)} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

