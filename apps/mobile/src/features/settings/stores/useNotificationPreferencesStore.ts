import { create } from 'zustand';

import {
  defaultNotificationPreferences,
  type NotificationPreferences,
} from '@/src/types/notification';

import { notificationPreferencesService } from '../services/notificationPreferencesService';

type NotificationPreferencesState = {
  preferences: NotificationPreferences;
  /** 저장된 값을 아직 읽지 않은 상태. 첫 로드 전에는 스위치를 조작할 수 없게 한다. */
  isLoading: boolean;
  saveErrorMessage?: string;
  load: () => Promise<void>;
  setPreference: (key: keyof NotificationPreferences, value: boolean) => Promise<void>;
};

export const useNotificationPreferencesStore = create<NotificationPreferencesState>((set, get) => ({
  preferences: defaultNotificationPreferences,
  isLoading: true,

  load: async () => {
    set({ isLoading: true });
    const stored = await notificationPreferencesService.getPreferences();
    set({ preferences: stored, isLoading: false, saveErrorMessage: undefined });
  },

  setPreference: async (key, value) => {
    const previous = get().preferences;
    const next = { ...previous, [key]: value };

    // 스위치는 즉시 반응시키고, 저장이 실패하면 이전 값으로 되돌린다.
    set({ preferences: next, saveErrorMessage: undefined });

    try {
      await notificationPreferencesService.savePreferences(next);
    } catch {
      set({
        preferences: previous,
        saveErrorMessage: '설정을 저장하지 못했어요. 잠시 후 다시 시도해 주세요.',
      });
    }
  },
}));
