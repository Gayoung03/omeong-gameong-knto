import { apiClient } from '@/src/services/apiClient';
import type { NotificationPreferences } from '@/src/types/notification';

export interface NotificationPreferencesService {
  getPreferences(): Promise<NotificationPreferences>;
  savePreferences(preferences: NotificationPreferences): Promise<void>;
}

export const notificationPreferencesService: NotificationPreferencesService = {
  async getPreferences() {
    const response = await apiClient.get<{ notificationPreferences: NotificationPreferences }>(
      '/users/me',
    );
    return response.data.notificationPreferences;
  },

  async savePreferences(preferences) {
    await apiClient.patch('/users/me/notification-preferences', preferences);
  },
};
