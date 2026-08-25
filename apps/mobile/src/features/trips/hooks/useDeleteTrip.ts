import { useMutation, useQueryClient } from '@tanstack/react-query';

import { deleteTrip } from '../api/tripsApi';
import { tripQueryKeys } from './useTrips';

/**
 * 여행 삭제.
 *
 * **되돌릴 수 없다.** 날짜·일정·체크리스트·메모가 함께 사라진다.
 * 다만 여행기록(travel_logs)은 남는다 — 서버가 `route_id` 만 비운다.
 * 사진과 기록은 여행과 별개로 사용자의 것이라서다.
 */
export function useDeleteTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (tripId: string) => deleteTrip(tripId).then(() => tripId),
    onSuccess: (tripId) => {
      // 상세 캐시는 지운다. 남겨두면 뒤로 가기로 없는 여행을 다시 열 수 있다.
      queryClient.removeQueries({ queryKey: tripQueryKeys.detail(tripId) });
      queryClient.invalidateQueries({ queryKey: tripQueryKeys.list() });
    },
  });
}
