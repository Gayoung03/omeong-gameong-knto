import AsyncStorage from '@react-native-async-storage/async-storage';

import {
  defaultNotificationPreferences,
  type NotificationPreferences,
} from '@/src/types/notification';

const STORAGE_KEY = 'notification-preferences';

export interface NotificationPreferencesService {
  getPreferences(): Promise<NotificationPreferences>;
  savePreferences(preferences: NotificationPreferences): Promise<void>;
}

/** 저장된 값에 없는 키는 기본값으로 채워, 항목이 늘어나도 이전 저장값을 그대로 쓸 수 있다. */
function parsePreferences(raw: string): NotificationPreferences {
  const parsed: unknown = JSON.parse(raw);
  if (typeof parsed !== 'object' || parsed === null) return defaultNotificationPreferences;

  const stored = parsed as Partial<NotificationPreferences>;
  return {
    inquiryAnswerEnabled:
      typeof stored.inquiryAnswerEnabled === 'boolean'
        ? stored.inquiryAnswerEnabled
        : defaultNotificationPreferences.inquiryAnswerEnabled,
    marketingEnabled:
      typeof stored.marketingEnabled === 'boolean'
        ? stored.marketingEnabled
        : defaultNotificationPreferences.marketingEnabled,
  };
}

/**
 * 기기 로컬(AsyncStorage) 구현체.
 * TODO: 실제 API 연동 시 이 객체만 서버 구현체로 교체
 *       (GET /users/me/notification-preferences, PATCH /users/me/notification-preferences)
 */
export const notificationPreferencesService: NotificationPreferencesService = {
  async getPreferences() {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultNotificationPreferences;

      return parsePreferences(raw);
    } catch {
      // 읽기에 실패해도 화면은 기본값으로 계속 동작해야 한다.
      return defaultNotificationPreferences;
    }
  },

  async savePreferences(preferences) {
    // 저장 실패는 호출부에서 되돌릴 수 있도록 그대로 던진다.
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  },
};
