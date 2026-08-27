export const PRIORITY_PRESETS = [
  {
    value: 'balanced',
    label: '균형 추천',
    description: '반려 편의·선호·동선·날씨를 고루 반영해요.',
  },
  {
    value: 'taste',
    label: '취향저격',
    description: '이번 여행에서 원하는 장소 유형을 더 반영해요.',
  },
  {
    value: 'pet',
    label: '반려최우선',
    description: '반려동물이 편하게 이용할 수 있는 장소를 더 반영해요.',
  },
  {
    value: 'proximity',
    label: '알찬동선',
    description: '기준점에서 가깝고 이동 부담이 적은 장소를 더 반영해요.',
  },
  {
    value: 'healing',
    label: '여유힐링',
    description: '강수확률과 실내·실외 환경의 적합도를 더 반영해요.',
  },
] as const;

export const USER_CRITERIA_OPTIONS = [
  { value: 'preference', label: '이번 여행 선호' },
  { value: 'pet', label: '반려 편의' },
  { value: 'proximity', label: '기준점 근접도' },
  { value: 'weather', label: '날씨 적합도' },
] as const;

export type PriorityPreset = (typeof PRIORITY_PRESETS)[number]['value'];
export type UserCriterion = (typeof USER_CRITERIA_OPTIONS)[number]['value'];

export type RecommendationPersonalizationPayload = {
  priorityPreset: PriorityPreset;
  userCriteria: UserCriterion[];
};

export function toPersonalizationPayload(
  priorityPreset: PriorityPreset,
  userCriteria: UserCriterion[],
): RecommendationPersonalizationPayload {
  return { priorityPreset, userCriteria: [...new Set(userCriteria)] };
}

export function isPriorityPreset(value: unknown): value is PriorityPreset {
  return PRIORITY_PRESETS.some((preset) => preset.value === value);
}

export function isUserCriterion(value: unknown): value is UserCriterion {
  return USER_CRITERIA_OPTIONS.some((criterion) => criterion.value === value);
}
