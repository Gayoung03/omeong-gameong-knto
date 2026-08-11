export type NotificationPreferences = {
  inquiryAnswerEnabled: boolean;
  marketingEnabled: boolean;
};

export const defaultNotificationPreferences: NotificationPreferences = {
  inquiryAnswerEnabled: true,
  marketingEnabled: false,
};
