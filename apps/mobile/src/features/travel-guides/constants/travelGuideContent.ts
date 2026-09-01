import type { IoniconName } from '@/src/features/home/types/home';

export type GuideTone = 'orange' | 'mint' | 'green' | 'blue' | 'warning' | 'neutral';

export type GuideBadge = {
  label: string;
  tone: GuideTone;
};

export type GuideFact = {
  label: string;
  value: string;
};

export type TransportGuide = {
  id: string;
  carrierName: string;
  category: 'airline' | 'ferry';
  route?: string;
  icon: IoniconName;
  verifiedLabel: string;
  sourceLabel: string;
  summary: string;
  badges: GuideBadge[];
  facts: GuideFact[];
  notes: string[];
  warning?: string;
};

export type PreparationGuide = {
  id: string;
  title: string;
  description: string;
  icon: IoniconName;
  verifiedLabel: string;
  badges: GuideBadge[];
};

export type ChecklistItem = {
  id: string;
  label: string;
  hint: string;
};

export type ChecklistSection = {
  id: string;
  title: string;
  icon: IoniconName;
  items: ChecklistItem[];
};

export const checklistSections: ChecklistSection[] = [
  {
    id: 'reservation',
    title: '예약·규정',
    icon: 'calendar-outline',
    items: [
      {
        id: 'confirm-carrier-rule',
        label: '항공사/선사 공식 안내 다시 확인',
        hint: '규정은 바뀔 수 있어 예약 직전에 확인해요.',
      },
      {
        id: 'request-pet-service',
        label: '반려동물 운송 사전 신청',
        hint: '24시간 전 마감이 있거나 확약이 필요한 곳이 있어요.',
      },
      {
        id: 'check-age-weight',
        label: '나이·무게·마릿수 조건 확인',
        hint: '무게는 DB 기준 모두 케이지 포함으로 봅니다.',
      },
      {
        id: 'check-breed-restriction',
        label: '단두종·맹견 등 견종 제한 확인',
        hint: '운송사마다 제한 범위가 다르니 공식 안내를 확인해요.',
      },
    ],
  },
  {
    id: 'carrier',
    title: '케이지·용품',
    icon: 'cube-outline',
    items: [
      {
        id: 'measure-carrier',
        label: '케이지 크기와 재질 확인',
        hint: '항공사는 좌석 아래 보관 조건까지 함께 봐야 해요.',
      },
      {
        id: 'prepare-pad',
        label: '배변패드와 여분 봉투 준비',
        hint: '기내에서는 케이지를 열고 교체하기 어렵습니다.',
      },
      {
        id: 'prepare-water',
        label: '물 급여 방식 확인',
        hint: '용기를 열지 않고 줄 수 있는 방식이 필요한 항공사가 있어요.',
      },
      {
        id: 'prepare-id-leash',
        label: '인식표·목줄·입마개 조건 확인',
        hint: '여객선은 항로별로 필요한 용품이 달라요.',
      },
    ],
  },
  {
    id: 'departure-day',
    title: '출발 당일',
    icon: 'time-outline',
    items: [
      {
        id: 'check-checkin',
        label: '온라인 체크인 가능 여부 확인',
        hint: '일부 항공사는 웹·모바일 체크인이 제한돼요.',
      },
      {
        id: 'check-temperature',
        label: '기온·기종·계절 제한 확인',
        hint: '혹서기와 혹한기에는 위탁이 제한될 수 있어요.',
      },
      {
        id: 'arrive-early',
        label: '체크인과 승선 수속 여유 있게 도착',
        hint: '서약서 작성이나 현장 확인 시간이 생길 수 있어요.',
      },
      {
        id: 'watch-condition',
        label: '아이 컨디션과 대기 시간 살피기',
        hint: '건강 판단은 수의사와 상의하고, 규정은 운송사에 확인해요.',
      },
    ],
  },
];
