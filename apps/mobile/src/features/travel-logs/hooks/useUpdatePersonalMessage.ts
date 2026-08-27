import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { TravelLog } from '@/src/types/travelLog';

import { updatePersonalMessage } from '../api/travelLogsApi';
import { tripLogsQueryKey } from './useTripMemoryLogs';

type UpdatePersonalMessageInput = {
  tripId: string;
  logId: string;
  message: string | null;
};

/** PATCH /travel-logs/{logId} 로 "나의 한 줄"을 저장한다. */
export function useUpdatePersonalMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ logId, message }: UpdatePersonalMessageInput) =>
      updatePersonalMessage(logId, message),
    onSuccess: (updatedLog, variables) => {
      queryClient.setQueryData<TravelLog[]>(tripLogsQueryKey(variables.tripId), (current) =>
        current?.map((log) => (log.logId === updatedLog.logId ? updatedLog : log)),
      );
    },
  });
}
