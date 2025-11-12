import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type ReactNode
} from 'react';
import dayjs from 'dayjs';
import type { MaxWebAppInitData } from '../types/maxWebApp';

export type AppTab = 'today' | 'calendar' | 'goals' | 'leaderboard';

interface AppState {
  activeTab: AppTab;
  isChatOpen: boolean;
  selectedGoalId: string | null;
  selectedDate: string;
  initData: MaxWebAppInitData | null;
}

type Action =
  | { type: 'SET_TAB'; tab: AppTab }
  | { type: 'SET_CHAT_OPEN'; value: boolean }
  | { type: 'SET_INIT_DATA'; initData: MaxWebAppInitData | null }
  | { type: 'SELECT_GOAL'; goalId: string | null }
  | { type: 'SET_SELECTED_DATE'; date: string };

const initialState: AppState = {
  activeTab: 'today',
  isChatOpen: false,
  selectedGoalId: null,
  selectedDate: dayjs().format('YYYY-MM-DD'),
  initData: null
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_TAB':
      return { ...state, activeTab: action.tab };
    case 'SET_CHAT_OPEN':
      return { ...state, isChatOpen: action.value };
    case 'SET_INIT_DATA':
      if (state.initData === action.initData) {
        return state;
      }
      return { ...state, initData: action.initData };
    case 'SELECT_GOAL':
      return { ...state, selectedGoalId: action.goalId };
    case 'SET_SELECTED_DATE':
      return { ...state, selectedDate: action.date };
    default:
      return state;
  }
}

interface AppStateContextValue extends AppState {
  setActiveTab: (tab: AppTab) => void;
  setChatOpen: (value: boolean) => void;
  setInitData: (data: MaxWebAppInitData | null) => void;
  selectGoal: (goalId: string | null) => void;
  setSelectedDate: (date: string) => void;
}

const AppStateContext = createContext<AppStateContextValue | null>(null);

export const AppStateProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const setActiveTab = useCallback((tab: AppTab) => {
    dispatch({ type: 'SET_TAB', tab });
  }, []);

  const setChatOpen = useCallback((value: boolean) => {
    dispatch({ type: 'SET_CHAT_OPEN', value });
  }, []);

  const setInitData = useCallback((data: MaxWebAppInitData | null) => {
    dispatch({ type: 'SET_INIT_DATA', initData: data });
  }, []);

  const selectGoal = useCallback((goalId: string | null) => {
    dispatch({ type: 'SELECT_GOAL', goalId });
  }, []);

  const setSelectedDate = useCallback((date: string) => {
    dispatch({ type: 'SET_SELECTED_DATE', date });
  }, []);

  const value = useMemo<AppStateContextValue>(
    () => ({
      ...state,
      setActiveTab,
      setChatOpen,
      setInitData,
      selectGoal,
      setSelectedDate
    }),
    [state, setActiveTab, setChatOpen, setInitData, selectGoal, setSelectedDate]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
};

export const useAppState = () => {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error('useAppState must be used within AppStateProvider');
  }
  return context;
};
