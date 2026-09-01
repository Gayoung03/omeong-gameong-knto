import { useQuery } from '@tanstack/react-query';

import { fetchNotifications } from '../api/notificationApi';

export function useNotifications() {
  return useQuery({ queryKey: ['notifications'], queryFn: fetchNotifications });
}
