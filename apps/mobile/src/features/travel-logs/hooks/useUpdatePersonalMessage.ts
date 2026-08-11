import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { TravelLog } from '@/src/types/travelLog';

import { updatePersonalMessage } from '../mocks/travelLogMocks';
import { tripLogsQueryKey } from './useTripMemoryLogs';

type UpdatePersonalMessageInput = {
  tripId: string;
  logId: string;
  message: string | null;
};

/**
 * 현재는 목업 mutation(updatePersonalMessage)을 감싼 것뿐이라 백엔드 저장은 되지 않는다.
 * TODO: 실제 수정 API가 생기면 mutationFn만 교체
 */
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
