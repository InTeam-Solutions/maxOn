import { useState, useEffect } from 'react';
import dayjs from 'dayjs';
import { apiClient } from '../services/api';
import styles from './WeekScheduleSelector.module.css';

interface TimeSlot {
  start: string; // "HH:mm"
  end: string;   // "HH:mm"
}

interface DaySchedule {
  dayOfWeek: number; // 0 = Monday, 6 = Sunday
  busySlots: TimeSlot[];
}

interface WeekScheduleSelectorProps {
  onSelect: (selectedDays: number[], preferredTime: string) => void;
  onCancel?: () => void;
}

const DAYS_OF_WEEK = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const HOURS_IN_DAY = 24;

export const WeekScheduleSelector = ({ onSelect, onCancel }: WeekScheduleSelectorProps) => {
  const [schedules, setSchedules] = useState<DaySchedule[]>([]);
  const [selectedDays, setSelectedDays] = useState<Set<number>>(new Set());
  const [preferredTime, setPreferredTime] = useState<string>('18:00');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSchedules();
  }, []);

  const loadSchedules = async () => {
    try {
      setLoading(true);
      // Get events for the next 7 days to analyze busy times
      const startDate = dayjs().format('YYYY-MM-DD');
      const endDate = dayjs().add(7, 'days').format('YYYY-MM-DD');

      const events = await apiClient.getEvents({ start_date: startDate, end_date: endDate });

      // Group events by day of week and extract busy time slots
      const daySchedules: DaySchedule[] = Array.from({ length: 7 }, (_, i) => ({
        dayOfWeek: i,
        busySlots: []
      }));

      events.forEach((event: any) => {
        if (event.time) {
          const eventDate = dayjs(event.date);
          const dayOfWeek = (eventDate.day() + 6) % 7; // Convert Sunday=0 to Monday=0

          // Parse time (assuming format like "14:00" or "14:00:00")
          const [hours, minutes] = event.time.split(':').map(Number);
          const startTime = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;

          // Assume 1 hour duration if not specified
          const endHours = (hours + 1) % 24;
          const endTime = `${String(endHours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;

          daySchedules[dayOfWeek].busySlots.push({ start: startTime, end: endTime });
        }
      });

      setSchedules(daySchedules);
    } catch (error) {
      console.error('Failed to load schedules:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleDay = (dayIndex: number) => {
    const newSelected = new Set(selectedDays);
    if (newSelected.has(dayIndex)) {
      newSelected.delete(dayIndex);
    } else {
      newSelected.add(dayIndex);
    }
    setSelectedDays(newSelected);
  };

  const handleSubmit = () => {
    if (selectedDays.size === 0) {
      alert('Выберите хотя бы один день недели');
      return;
    }
    onSelect(Array.from(selectedDays), preferredTime);
  };

  // Calculate busy percentage for a specific hour
  const calculateBusyPercentage = (daySchedule: DaySchedule, hour: number): number => {
    const hourStart = hour;
    const hourEnd = hour + 1;

    for (const slot of daySchedule.busySlots) {
      const [slotStartHour] = slot.start.split(':').map(Number);
      const [slotEndHour] = slot.end.split(':').map(Number);

      // Check if this hour overlaps with any busy slot
      if (slotStartHour <= hourStart && hourEnd <= slotEndHour) {
        return 100; // Fully busy
      }
      if (slotStartHour < hourEnd && slotEndHour > hourStart) {
        return 50; // Partially busy
      }
    }
    return 0; // Free
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Загрузка расписания...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Когда вам удобно заниматься?</h3>
      <p className={styles.subtitle}>
        Красные линии показывают время, когда у вас уже запланированы события
      </p>

      <div className={styles.daysGrid}>
        {DAYS_OF_WEEK.map((dayName, dayIndex) => {
          const daySchedule = schedules[dayIndex];
          const isSelected = selectedDays.has(dayIndex);

          return (
            <div
              key={dayIndex}
              className={`${styles.dayCard} ${isSelected ? styles.selected : ''}`}
              onClick={() => toggleDay(dayIndex)}
            >
              <div className={styles.dayHeader}>{dayName}</div>
              <div className={styles.timeVisualization}>
                {Array.from({ length: HOURS_IN_DAY }).map((_, hour) => {
                  const busyPercentage = calculateBusyPercentage(daySchedule, hour);
                  const opacity = busyPercentage / 100;

                  return (
                    <div
                      key={hour}
                      className={styles.hourSlot}
                      style={{
                        backgroundColor: busyPercentage > 0 ? `rgba(239, 68, 68, ${opacity})` : 'transparent'
                      }}
                      title={`${hour}:00 - ${hour + 1}:00 ${busyPercentage > 0 ? '(занято)' : ''}`}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.timeSelector}>
        <label className={styles.label}>
          Предпочтительное время начала:
          <input
            type="time"
            value={preferredTime}
            onChange={(e) => setPreferredTime(e.target.value)}
            className={styles.timeInput}
          />
        </label>
      </div>

      <div className={styles.actions}>
        {onCancel && (
          <button onClick={onCancel} className={styles.cancelButton}>
            Отмена
          </button>
        )}
        <button onClick={handleSubmit} className={styles.submitButton}>
          Продолжить
        </button>
      </div>
    </div>
  );
};
