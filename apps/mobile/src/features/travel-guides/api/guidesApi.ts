import { isAxiosError } from 'axios';

import { apiClient } from '@/src/services/apiClient';

import type {
  GuideBadge,
  GuideTone,
  PreparationGuide,
  TransportGuide,
} from '../constants/travelGuideContent';

type GuideCategoryApi = 'airline' | 'ferry' | 'preparation';
type CarrierTypeApi = 'airline' | 'ferry';

type GuideSourceResponse = {
  sourceName: string;
  sourceUrl: string | null;
  sourceNote: string | null;
  verifiedAt: string | null;
};

type GuideDocumentListItemResponse = {
  id: string;
  slug: string;
  title: string;
  category: GuideCategoryApi;
  summary: string;
  verifiedAt: string | null;
  sources: GuideSourceResponse[];
};

type GuideDocumentListResponse = {
  items: GuideDocumentListItemResponse[];
  total: number;
  limit: number;
  offset: number;
};

type TransportRuleResponse = {
  id: string;
  guideDocumentId: string;
  guideSlug: string;
  guideTitle: string;
  category: GuideCategoryApi;
  carrierName: string;
  carrierType: CarrierTypeApi;
  route: string | null;
  cabinAllowed: boolean | null;
  cabinMaxWeightKg: number | null;
  cabinFeeKrw: number | null;
  minAgeWeeksCabin: number | null;
  maxPetsPerPersonCabin: number | null;
  maxPetsPerTrip: number | null;
  cargoAllowed: boolean | null;
  cargoMaxWeightKg: number | null;
  cargoFeeThresholdKg: number | null;
  cargoFeeLightKrw: number | null;
  cargoFeeHeavyKrw: number | null;
  minAgeWeeksCargo: number | null;
  pledgeRequired: boolean | null;
  onlineCheckinAllowed: boolean | null;
  sameDayRequestAllowed: boolean | null;
  requestDeadlineHours: number | null;
  airportCagePriceKrw: number | null;
  durationMinutes: number | null;
  notes: string | null;
  sourceUrl: string | null;
  verifiedAt: string | null;
  sources: GuideSourceResponse[];
};

type TransportRuleListResponse = {
  items: TransportRuleResponse[];
  total: number;
  limit: number;
  offset: number;
};

export type TravelGuideOverview = {
  airlineGuides: TransportGuide[];
  ferryGuides: TransportGuide[];
  preparationGuides: PreparationGuide[];
  guideCount: number;
  ruleCount: number;
  latestVerifiedLabel: string;
};

const PREPARATION_META: Record<string, { icon: PreparationGuide['icon']; badges: GuideBadge[] }> = {
  'prep-rental-car': {
    icon: 'car-outline',
    badges: [
      { label: '업체별 확인', tone: 'orange' },
      { label: '차량 옵션', tone: 'blue' },
    ],
  },
  'prep-packing': {
    icon: 'bag-outline',
    badges: [
      { label: '준비물', tone: 'mint' },
      { label: '운송 규정 기반', tone: 'green' },
    ],
  },
  'prep-first-trip': {
    icon: 'paw-outline',
    badges: [
      { label: '첫 여행', tone: 'orange' },
      { label: '동선 여유', tone: 'mint' },
    ],
  },
  'prep-jeju-entry': {
    icon: 'document-text-outline',
    badges: [
      { label: '행정 자료', tone: 'green' },
      { label: '개·고양이', tone: 'mint' },
    ],
  },
};

function formatDateLabel(value: string | null, fallback = '확인일 미등록') {
  if (!value) return fallback;
  return `${value.slice(0, 10).replaceAll('-', '.')} 확인`;
}

function formatLatestVerifiedLabel(values: (string | null)[]) {
  const latest = values
    .filter((value): value is string => Boolean(value))
    .map((value) => value.slice(0, 10))
    .sort()
    .at(-1);

  return latest ? `${latest.replaceAll('-', '.')} 기준` : '확인일 미등록';
}

function formatKg(value: number | null) {
  if (value === null) return null;
  return Number.isInteger(value) ? `${value}kg` : `${value.toFixed(1)}kg`;
}

function formatMinutes(value: number | null) {
  if (value === null) return null;
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  if (hours === 0) return `${minutes}분`;
  if (minutes === 0) return `${hours}시간`;
  return `${hours}시간 ${minutes}분`;
}

function formatFee(value: number | null) {
  if (value === null) return null;
  if (value % 10000 === 0) return `${value / 10000}만 원`;
  if (value % 1000 === 0 && value > 10000) {
    const man = Math.floor(value / 10000);
    const cheon = (value % 10000) / 1000;
    return `${man}만 ${cheon}천 원`;
  }
  return `${value.toLocaleString('ko-KR')}원`;
}

function formatCabin(rule: TransportRuleResponse) {
  if (rule.cabinAllowed === false) return '불가';
  const weight = formatKg(rule.cabinMaxWeightKg);
  if (rule.cabinAllowed && weight) return `케이지 포함 ${weight} 이하`;
  if (rule.cabinAllowed) return '가능';
  return '확인 필요';
}

function formatCargo(rule: TransportRuleResponse) {
  if (rule.cargoAllowed === false) return '불가';
  const weight = formatKg(rule.cargoMaxWeightKg);
  if (rule.cargoAllowed && weight) return `케이지 포함 ${weight} 이하`;
  if (rule.cargoAllowed) return '가능';
  return '해당 없음';
}

function formatAirlineFee(rule: TransportRuleResponse) {
  const cabinFee = formatFee(rule.cabinFeeKrw);
  const cargoLightFee = formatFee(rule.cargoFeeLightKrw);
  const cargoHeavyFee = formatFee(rule.cargoFeeHeavyKrw);
  const threshold = formatKg(rule.cargoFeeThresholdKg);

  if (cabinFee && cargoLightFee && cargoHeavyFee && threshold) {
    return `기내 ${cabinFee}, 위탁 ${threshold} 이하 ${cargoLightFee}/초과 ${cargoHeavyFee}`;
  }
  if (cabinFee) return `기내 ${cabinFee}`;
  if (cargoLightFee && cargoHeavyFee && threshold) {
    return `위탁 ${threshold} 이하 ${cargoLightFee}, 초과 ${cargoHeavyFee}`;
  }
  return '확인 필요';
}

function formatDeadline(rule: TransportRuleResponse) {
  if (rule.requestDeadlineHours !== null) {
    return `출발 ${rule.requestDeadlineHours}시간 전`;
  }
  if (rule.sameDayRequestAllowed === true) return '현장 신청 가능 여부 확인';
  if (rule.sameDayRequestAllowed === false) return '당일 신청 불가';
  return '공식 안내 확인';
}

function firstSentence(value: string | null, fallback: string) {
  const text = value?.trim();
  if (!text) return fallback;
  const [first] = text.split('. ');
  const sentence = first.endsWith('.') ? first : `${first}.`;
  return sentence.length > 78 ? `${sentence.slice(0, 77).trim()}…` : sentence;
}

function splitNotes(value: string | null) {
  if (!value) return [];
  return value
    .split('. ')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => (part.endsWith('.') ? part : `${part}.`));
}

function sourceLabel(sources: GuideSourceResponse[], sourceUrl: string | null) {
  if (sources.length > 0) return sources.map((source) => source.sourceName).join(' · ');
  return sourceUrl ?? '공식 출처 확인 필요';
}

function badge(label: string, tone: GuideTone): GuideBadge {
  return { label, tone };
}

function toTransportBadges(rule: TransportRuleResponse): GuideBadge[] {
  const badges: GuideBadge[] = [];
  const cabinWeight = formatKg(rule.cabinMaxWeightKg);
  const cargoWeight = formatKg(rule.cargoMaxWeightKg);
  const duration = formatMinutes(rule.durationMinutes);

  if (rule.carrierType === 'ferry') {
    badges.push(
      rule.cabinAllowed === false ? badge('원칙 불가', 'warning') : badge('동반 가능', 'green'),
    );
    if (duration) badges.push(badge(duration, 'mint'));
    if (rule.route) badges.push(badge(rule.route, 'blue'));
    return badges;
  }

  if (rule.cabinAllowed === false) {
    badges.push(badge('기내 불가', 'warning'));
  } else if (cabinWeight) {
    badges.push(badge(`기내 ${cabinWeight}`, 'mint'));
  }

  if (rule.cargoAllowed === false) {
    badges.push(badge('위탁 없음', 'warning'));
  } else if (cargoWeight) {
    badges.push(badge(`위탁 ${cargoWeight}`, 'green'));
  }

  if (rule.requestDeadlineHours !== null) {
    badges.push(badge(`${rule.requestDeadlineHours}시간 전`, 'orange'));
  } else if (rule.pledgeRequired) {
    badges.push(badge('서약서', 'orange'));
  }

  if (badges.length < 3 && rule.onlineCheckinAllowed === false) {
    badges.push(badge('온라인 제한', 'blue'));
  }

  return badges.slice(0, 3);
}

function airlineFacts(rule: TransportRuleResponse) {
  return [
    { label: '기내 동반', value: formatCabin(rule) },
    { label: '위탁 운송', value: formatCargo(rule) },
    { label: '국내선 요금', value: formatAirlineFee(rule) },
    { label: '신청 마감', value: formatDeadline(rule) },
  ];
}

function ferryFacts(rule: TransportRuleResponse) {
  return [
    { label: '항로', value: rule.route ?? '확인 필요' },
    { label: '소요 시간', value: formatMinutes(rule.durationMinutes) ?? '확인 필요' },
    { label: '동반 여부', value: rule.cabinAllowed === false ? '원칙적으로 불가' : '가능' },
    { label: '무게 제한', value: formatKg(rule.cabinMaxWeightKg) ?? '명시 없음' },
  ];
}

function warningFrom(rule: TransportRuleResponse) {
  if (rule.carrierType === 'airline' && rule.cargoAllowed === false) {
    return '기내 무게를 넘는 아이는 이 항공사로 이동하기 어렵습니다.';
  }
  if (rule.carrierType === 'airline' && rule.requestDeadlineHours === null) {
    return '사전 신청 마감 시점은 공식 안내에서 다시 확인해 주세요.';
  }
  if (rule.carrierType === 'ferry' && rule.cabinAllowed === false) {
    return '반려동물과 함께라면 다른 항로를 먼저 비교해 주세요.';
  }
  return undefined;
}

function toTransportGuide(rule: TransportRuleResponse): TransportGuide {
  const category = rule.carrierType;
  return {
    id: rule.id,
    carrierName: rule.carrierName,
    category,
    route: rule.route ?? undefined,
    icon: category === 'airline' ? 'airplane' : 'boat',
    verifiedLabel: formatDateLabel(rule.verifiedAt),
    sourceLabel: sourceLabel(rule.sources, rule.sourceUrl),
    summary: firstSentence(rule.notes, rule.guideTitle),
    badges: toTransportBadges(rule),
    facts: category === 'airline' ? airlineFacts(rule) : ferryFacts(rule),
    notes: splitNotes(rule.notes),
    warning: warningFrom(rule),
  };
}

function toPreparationGuide(document: GuideDocumentListItemResponse): PreparationGuide {
  const meta = PREPARATION_META[document.slug] ?? {
    icon: 'document-text-outline' as const,
    badges: [badge('준비 가이드', 'neutral')],
  };
  return {
    id: document.slug,
    title: document.title,
    description: document.summary,
    icon: meta.icon,
    verifiedLabel: formatDateLabel(document.verifiedAt),
    badges: meta.badges,
  };
}

export async function getTravelGuideOverview(): Promise<TravelGuideOverview> {
  const [guidesResponse, rulesResponse] = await Promise.all([
    apiClient.get<GuideDocumentListResponse>('/guides', { params: { limit: 100 } }),
    apiClient.get<TransportRuleListResponse>('/guides/transport-rules', {
      params: { limit: 100 },
    }),
  ]);

  const transportGuides = rulesResponse.data.items.map(toTransportGuide);
  const preparationGuides = guidesResponse.data.items
    .filter((guide) => guide.category === 'preparation')
    .map(toPreparationGuide);
  const verifiedDates = [
    ...guidesResponse.data.items.map((guide) => guide.verifiedAt),
    ...rulesResponse.data.items.map((rule) => rule.verifiedAt),
  ];

  return {
    airlineGuides: transportGuides.filter((guide) => guide.category === 'airline'),
    ferryGuides: transportGuides.filter((guide) => guide.category === 'ferry'),
    preparationGuides,
    guideCount: guidesResponse.data.total,
    ruleCount: rulesResponse.data.total,
    latestVerifiedLabel: formatLatestVerifiedLabel(verifiedDates),
  };
}

export async function getTravelGuideDetail(guideId: string): Promise<TransportGuide | null> {
  try {
    const { data } = await apiClient.get<TransportRuleResponse>(
      `/guides/transport-rules/${guideId}`,
    );
    return toTransportGuide(data);
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}
