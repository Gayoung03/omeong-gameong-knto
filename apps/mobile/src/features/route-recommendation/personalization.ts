export const PRIORITY_PRESETS = [
  {
    value: 'balanced',
    label: '골고루 추천해주세요',
    description: '취향, 반려동물, 이동 거리와 날씨를 고르게 살펴봐요.',
  },
  {
    value: 'taste',
    label: '취향에 맞는 여행',
    description: '선택한 장소 유형과 잘 맞는 곳을 우선 추천해요.',
  },
  {
    value: 'pet',
    label: '우리 아이 중심 여행',
    description: '반려동물이 이용하기 편하고 조건이 잘 확인된 곳을 우선 추천해요.',
  },
  {
    value: 'proximity',
    label: '이동이 편한 여행',
    description: '숙소나 출발지에서 가깝고 이동 부담이 적은 곳을 우선 추천해요.',
  },
  {
    value: 'healing',
    label: '날씨에 맞는 여행',
    description: '여행 날짜의 날씨와 실내·실외 환경을 고려해 추천해요.',
  },
] as const;

export const USER_CRITERIA_OPTIONS = [
  { value: 'preference', label: '내 취향에 맞는 곳' },
  { value: 'pet', label: '우리 아이가 편한 곳' },
  { value: 'proximity', label: '이동이 편한 코스' },
  { value: 'weather', label: '날씨에 맞는 장소' },
] as const;

export type PriorityPreset = (typeof PRIORITY_PRESETS)[number]['value'];
export type UserCriterion = (typeof USER_CRITERIA_OPTIONS)[number]['value'];
export type PriorityMode = 'manual' | 'preset';

export type RecommendationPersonalizationPayload = {
  priorityPreset: PriorityPreset;
  userCriteria: UserCriterion[];
};

export function toPersonalizationPayload(
  mode: PriorityMode,
  priorityPreset: PriorityPreset,
  userCriteria: UserCriterion[],
): RecommendationPersonalizationPayload {
  return mode === 'manual'
    ? { priorityPreset: 'balanced', userCriteria: [...new Set(userCriteria)].slice(0, 3) }
    : { priorityPreset, userCriteria: [] };
}

export function isPriorityPreset(value: unknown): value is PriorityPreset {
  return PRIORITY_PRESETS.some((preset) => preset.value === value);
}

export function isUserCriterion(value: unknown): value is UserCriterion {
  return USER_CRITERIA_OPTIONS.some((criterion) => criterion.value === value);
}
