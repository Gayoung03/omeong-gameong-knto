import { create } from 'zustand';

import type { TravelLog } from '@/src/types/travelLog';

type SavedLogState = {
  savedLogs: TravelLog[];
  addSavedLog: (log: TravelLog) => void;
};

export const useSavedLogStore = create<SavedLogState>((set) => ({
  savedLogs: [],
  addSavedLog: (log) =>
    set((state) => ({ savedLogs: [log, ...state.savedLogs.filter((item) => item.logId !== log.logId)] })),
}));
