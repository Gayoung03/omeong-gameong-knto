import type { ActivitySummary } from './profile';

export interface User {
  userId: string;
  nickname: string;
  email: string;
  profileImage: string;
  activitySummary: ActivitySummary;
}
