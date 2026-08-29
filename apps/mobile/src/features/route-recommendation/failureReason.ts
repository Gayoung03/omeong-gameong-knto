import type { RouteFailureReason } from '@/src/features/trips/types/routeApi';

const FAILURE_GUIDANCE: Record<RouteFailureReason, string> = {
  LOCATION_NOT_FOUND: '출발지나 숙소 위치를 확인하지 못했어요. 주소를 다시 확인해주세요.',
  NO_RECOMMENDABLE_PLACES:
    '선택한 조건에 맞는 반려동물 동반 장소가 부족해요. 조건을 조금 넓혀주세요.',
  DINNER_RESTAURANT_SHORTAGE:
    '저녁 시간에 배치할 반려동물 동반 식당이 부족해요. 날짜나 조건을 조정해주세요.',
  ROUTE_PROVIDER_FAILED: '이동 경로를 확인하지 못했어요. 잠시 후 다시 시도해주세요.',
  GENERATION_TIMEOUT: '추천 생성 시간이 초과됐어요. 잠시 후 다시 시도해주세요.',
  UNKNOWN: '루트를 생성하지 못했어요. 조건을 확인하고 다시 요청해주세요.',
};

export function failureGuidance(reason: RouteFailureReason | null | undefined): string {
  return FAILURE_GUIDANCE[reason ?? 'UNKNOWN'];
}
