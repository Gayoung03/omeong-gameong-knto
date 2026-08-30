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

export const guideSummary = {
  guideCount: 15,
  ruleCount: 12,
  latestVerifiedLabel: '2026.08.27 기준',
};

export const airlineGuides: TransportGuide[] = [
  {
    id: 'airline-korean-air',
    carrierName: '대한항공',
    category: 'airline',
    icon: 'airplane',
    verifiedLabel: '2026.08.26 확인',
    sourceLabel: '대한항공 반려동물 동반 안내',
    summary: '기내 7kg, 위탁 45kg까지 확인된 대표 항공사예요.',
    badges: [
      { label: '기내 7kg', tone: 'mint' },
      { label: '위탁 45kg', tone: 'green' },
      { label: '24시간 전', tone: 'orange' },
    ],
    facts: [
      { label: '기내 동반', value: '케이지 포함 7kg 이하' },
      { label: '위탁 운송', value: '케이지 포함 45kg 이하' },
      { label: '국내선 요금', value: '32kg 이하 3만 원, 초과 6만 원' },
      { label: '신청 마감', value: '출발 24시간 전' },
    ],
    notes: [
      '기내 1마리, 위탁 2마리까지예요.',
      '보잉 737·A321은 6~9월 국내선 위탁이 제한돼요.',
      '단두종은 위탁이 어렵고 기내 조건에 맞을 때만 가능해요.',
    ],
    warning: '여름에 큰 아이와 이동한다면 예약 전 기종을 꼭 확인해 주세요.',
  },
  {
    id: 'airline-asiana',
    carrierName: '아시아나항공',
    category: 'airline',
    icon: 'airplane',
    verifiedLabel: '2026.08.26 확인',
    sourceLabel: '아시아나항공 반려동물 운송 안내',
    summary: '기내도 생후 16주 이상이라는 점이 다른 항공사와 달라요.',
    badges: [
      { label: '기내 7kg', tone: 'mint' },
      { label: '위탁 45kg', tone: 'green' },
      { label: '확약 필수', tone: 'warning' },
    ],
    facts: [
      { label: '기내 동반', value: '케이지 포함 7kg 이하' },
      { label: '위탁 운송', value: '케이지 포함 45kg 이하' },
      { label: '국내선 요금', value: '32kg 이하 3만 원, 초과 6만 원' },
      { label: '나이 기준', value: '기내·위탁 모두 생후 16주 이상' },
    ],
    notes: [
      '성인 탑승객만 신청할 수 있어요.',
      '예약·확약 없이 공항에 가면 기내와 위탁 모두 어렵습니다.',
      '에어부산 공동운항편은 위탁 서비스가 없어요.',
    ],
    warning: '공항 현장 접수로 해결하기 어려운 항공사라 사전 확약이 중요해요.',
  },
  {
    id: 'airline-jeju-air',
    carrierName: '제주항공',
    category: 'airline',
    icon: 'airplane',
    verifiedLabel: '2026.08.26 확인',
    sourceLabel: '제주항공 반려동물 운송 서비스',
    summary: '기내 9kg까지 가능하지만 화물칸 위탁은 없어요.',
    badges: [
      { label: '기내 9kg', tone: 'mint' },
      { label: '위탁 없음', tone: 'warning' },
      { label: '좌석 제한', tone: 'blue' },
    ],
    facts: [
      { label: '기내 동반', value: '케이지 포함 9kg 이하' },
      { label: '위탁 운송', value: '불가' },
      { label: '국내선 요금', value: '2만 5천 원' },
      { label: '체크인', value: '온라인 체크인 제한' },
    ],
    notes: [
      '반려동물 전용 좌석 6석을 이용해요.',
      '운송 서약서가 필요해요.',
      '위탁이 없어 단두종 위탁 제한은 해당하지 않아요.',
    ],
    warning: '9kg을 넘는 아이는 제주항공으로 이동하기 어렵습니다.',
  },
  {
    id: 'airline-tway',
    carrierName: '티웨이항공',
    category: 'airline',
    icon: 'airplane',
    verifiedLabel: '2026.08.26 확인',
    sourceLabel: "티웨이항공 t'pet 국내선 반려동물 운송규정",
    summary: '기내 9kg까지 가능하고, 신청 경로별 마감 시간이 달라요.',
    badges: [
      { label: '기내 9kg', tone: 'mint' },
      { label: '위탁 없음', tone: 'warning' },
      { label: '현장 가능', tone: 'orange' },
    ],
    facts: [
      { label: '기내 동반', value: '케이지 포함 9kg 이하' },
      { label: '위탁 운송', value: '불가' },
      { label: '국내선 요금', value: '3만 원' },
      { label: '신청 마감', value: '온라인 1일 전, 유선 2시간 30분 전' },
    ],
    notes: [
      '운송 서약서가 필요해요.',
      '온라인 체크인은 제한돼요.',
      '여정을 변경하면 반려동물 신청이 자동 취소돼요.',
    ],
    warning: '항공권을 바꾸면 반려동물 신청도 다시 확인해 주세요.',
  },
  {
    id: 'airline-jin-air',
    carrierName: '진에어',
    category: 'airline',
    icon: 'airplane',
    verifiedLabel: '2026.08.26 확인',
    sourceLabel: '진에어 JINI PET 반려동물 동반 여행 서비스',
    summary: '기내 9kg, 위탁 45kg까지 가능하지만 마감 시점은 명시가 없어요.',
    badges: [
      { label: '기내 9kg', tone: 'mint' },
      { label: '위탁 45kg', tone: 'green' },
      { label: '서약서', tone: 'orange' },
    ],
    facts: [
      { label: '기내 동반', value: '케이지 포함 9kg 이하' },
      { label: '위탁 운송', value: '케이지 포함 45kg 이하' },
      { label: '국내선 요금', value: '기내 2만 원, 위탁 3만/6만 원' },
      { label: '체크인', value: '온라인 체크인 제한' },
    ],
    notes: [
      '위탁은 1인 2마리, 항공기당 최대 5마리예요.',
      '운송 서약서가 필요해요.',
      '단두종은 위탁이 어려워요.',
    ],
    warning: '사전 신청 마감 시점은 DB에 명확한 값이 없어 공식 안내 확인이 필요해요.',
  },
  {
    id: 'airline-air-busan',
    carrierName: '에어부산',
    category: 'airline',
    icon: 'airplane',
    verifiedLabel: '2026.08.26 확인',
    sourceLabel: '에어부산 반려동물 운송 안내',
    summary: '기내 9kg, 위탁 32kg까지라 위탁 상한이 낮은 편이에요.',
    badges: [
      { label: '기내 9kg', tone: 'mint' },
      { label: '위탁 32kg', tone: 'green' },
      { label: '창가 좌석', tone: 'blue' },
    ],
    facts: [
      { label: '기내 동반', value: '케이지 포함 9kg 이하' },
      { label: '위탁 운송', value: '케이지 포함 32kg 이하' },
      { label: '국내선 요금', value: '기내 2만 원, 위탁 요금 확인 필요' },
      { label: '좌석', value: '반려동물 동반 시 창가 좌석' },
    ],
    notes: [
      '운송 서약서가 필요해요.',
      '혹한기에는 위탁이 제한될 수 있어요.',
      '예약센터 확약이 필요한 항목이 있어요.',
    ],
    warning: '32kg을 넘는 아이는 다른 항공사나 여객선도 함께 비교해 주세요.',
  },
  {
    id: 'airline-eastar-jet',
    carrierName: '이스타항공',
    category: 'airline',
    icon: 'airplane',
    verifiedLabel: '2026.08.26 확인',
    sourceLabel: '이스타항공 반려동물을 동반하는 고객 안내',
    summary: '기내 9kg까지 가능하고, 국내 운송 가능 노선을 명시해 둔 항공사예요.',
    badges: [
      { label: '기내 9kg', tone: 'mint' },
      { label: '위탁 없음', tone: 'warning' },
      { label: '24시간 전', tone: 'orange' },
    ],
    facts: [
      { label: '기내 동반', value: '케이지 포함 9kg 이하' },
      { label: '위탁 운송', value: '불가' },
      { label: '국내선 요금', value: '3만 원' },
      { label: '신청 마감', value: '출발 24시간 전' },
    ],
    notes: [
      '김포·제주·청주·군산·부산 노선을 명시하고 있어요.',
      '온라인 체크인은 제한돼요.',
      '취소·환불도 출발 24시간 전까지만 가능해요.',
    ],
    warning: '탑승 전 반려동물이 케이지에 들어가 있어야 합니다.',
  },
];

export const ferryGuides: TransportGuide[] = [
  {
    id: 'ferry-hanil-wando',
    carrierName: '한일고속페리',
    category: 'ferry',
    route: '완도↔제주',
    icon: 'boat',
    verifiedLabel: '2026.08.27 확인',
    sourceLabel: '한일고속페리 승선절차·선박 정보',
    summary: '완도에서 제주로 가는 2시간 40분 항로예요.',
    badges: [
      { label: '동반 가능', tone: 'green' },
      { label: '2시간 40분', tone: 'mint' },
      { label: '케이지 필수', tone: 'orange' },
    ],
    facts: [
      { label: '항로', value: '완도↔제주' },
      { label: '소요 시간', value: '2시간 40분' },
      { label: '동반 조건', value: '반려동물 객실 구매 필요' },
      { label: '무게 제한', value: '명시 없음' },
    ],
    notes: [
      '반려동물 객실을 구매하지 않으면 동반 승선이 어려워요.',
      '케이지가 필요하고 유모차·슬링백은 사용할 수 없어요.',
      '갑판 산책은 불가해요.',
    ],
  },
  {
    id: 'ferry-seaworld-mokpo',
    carrierName: '씨월드고속훼리',
    category: 'ferry',
    route: '목포↔제주',
    icon: 'boat',
    verifiedLabel: '2026.08.27 확인',
    sourceLabel: '씨월드고속훼리 반려동물 예약 안내·운항 스케줄',
    summary: '객실 등급이 무게로 나뉘는 목포 출발 장거리 항로예요.',
    badges: [
      { label: '동반 가능', tone: 'green' },
      { label: '최대 4시간 50분', tone: 'mint' },
      { label: '객실 등급', tone: 'blue' },
    ],
    facts: [
      { label: '항로', value: '목포↔제주' },
      { label: '소요 시간', value: '4시간 15분~4시간 50분' },
      { label: '객실 기준', value: '4kg·10kg 기준 객실 등급 구분' },
      { label: '전용 공간', value: '야외 펫가든 있음' },
    ],
    notes: [
      '펫코노미는 4kg 미만, 펫스탠다드룸·퀸메리 의자석은 10kg 미만 기준이에요.',
      '펫스위트룸은 무게 제한이 명시되어 있지 않아요.',
      '정기휴항이 배마다 달라 왕복 배편 확인이 필요해요.',
    ],
  },
  {
    id: 'ferry-seaworld-jindo',
    carrierName: '씨월드고속훼리',
    category: 'ferry',
    route: '진도↔제주',
    icon: 'boat',
    verifiedLabel: '2026.08.27 확인',
    sourceLabel: '씨월드고속훼리 반려동물 예약 안내·운항 스케줄',
    summary: '네 항로 중 가장 짧지만 항해 내내 케이지 안에 있어야 해요.',
    badges: [
      { label: '동반 가능', tone: 'green' },
      { label: '2시간', tone: 'mint' },
      { label: '좌석제', tone: 'orange' },
    ],
    facts: [
      { label: '항로', value: '진도↔제주' },
      { label: '소요 시간', value: '2시간' },
      { label: '이용 방식', value: '객실이 아닌 좌석제' },
      { label: '무게 제한', value: '명시 없음' },
    ],
    notes: [
      '추자도를 25분 경유하고 그동안에도 케이지를 열 수 없어요.',
      '펫가든은 없어요.',
      '1·3주 수요일은 휴항이에요.',
    ],
  },
  {
    id: 'ferry-oceanvista-samcheonpo',
    carrierName: '오션비스타제주',
    category: 'ferry',
    route: '삼천포↔제주',
    icon: 'boat',
    verifiedLabel: '2026.08.27 확인',
    sourceLabel: '오션비스타제주 펫룸 안내·운항 시간표',
    summary: '23:30 출발, 06:00 도착하는 심야 항로예요.',
    badges: [
      { label: '동반 가능', tone: 'green' },
      { label: '6시간 30분', tone: 'mint' },
      { label: '심야 운항', tone: 'blue' },
    ],
    facts: [
      { label: '항로', value: '삼천포↔제주' },
      { label: '소요 시간', value: '6시간 30분' },
      { label: '펫룸 조건', value: '케이지·입마개·목줄 계속 착용' },
      { label: '휴항', value: '매주 토요일' },
    ],
    notes: [
      '펫룸 안에서도 케이지와 입마개, 목줄을 계속 착용해야 해요.',
      '소프트케이지·슬링백·유모차형은 불가해요.',
      '인식표와 개인 이불을 준비해야 해요.',
    ],
    warning: '아이에게 6시간 30분 케이지 시간이 괜찮을지 먼저 판단해 주세요.',
  },
  {
    id: 'ferry-arion-nokdong',
    carrierName: '아리온제주',
    category: 'ferry',
    route: '고흥 녹동↔제주',
    icon: 'boat',
    verifiedLabel: '2026.08.27 확인',
    sourceLabel: '남해고속 운항시간표·FAQ',
    summary: '안내상 애완견 동승이 원칙적으로 불가한 항로예요.',
    badges: [
      { label: '원칙 불가', tone: 'warning' },
      { label: '3시간 40분', tone: 'mint' },
      { label: '예외 확인', tone: 'orange' },
    ],
    facts: [
      { label: '항로', value: '고흥 녹동↔제주' },
      { label: '소요 시간', value: '3시간 40분' },
      { label: '동반 여부', value: '원칙적으로 불가' },
      { label: '예외 조건', value: '케이지 보관, 지정 장소 이용' },
    ],
    notes: [
      '부득이한 경우에만 케이지에 넣어 예외적으로 허용돼요.',
      '객실은 이용할 수 없고 승무원이 지정한 곳에 보관해야 해요.',
      '민원이 우려되면 승선이 제한될 수 있어요.',
    ],
    warning: '반려동물과 함께라면 완도·목포·진도·삼천포 노선을 먼저 비교해 주세요.',
  },
];

export const transportGuides: TransportGuide[] = [...airlineGuides, ...ferryGuides];

export function findTransportGuide(guideId: string): TransportGuide | undefined {
  return transportGuides.find((guide) => guide.id === guideId);
}

export const preparationGuides: PreparationGuide[] = [
  {
    id: 'prep-rental-car',
    title: '제주에서 렌터카 이용하기',
    description: '렌터카는 업체·지점·예약 플랫폼마다 반려동물 조건이 달라 예약 전 확인이 필요해요.',
    icon: 'car-outline',
    verifiedLabel: '2026.08.27 확인',
    badges: [
      { label: '업체별 확인', tone: 'orange' },
      { label: '차량 옵션', tone: 'blue' },
    ],
  },
  {
    id: 'prep-packing',
    title: '제주 갈 때 챙길 것',
    description: '케이지, 배변패드, 급수 방식, 서약서처럼 운송 규정에서 반복되는 준비물을 모았어요.',
    icon: 'bag-outline',
    verifiedLabel: '2026.08.27 확인',
    badges: [
      { label: '준비물', tone: 'mint' },
      { label: '운송 규정 기반', tone: 'green' },
    ],
  },
  {
    id: 'prep-first-trip',
    title: '반려동물과 첫 여행',
    description: '처음 제주로 떠날 때 이동수단 선택, 대기 시간, 아이 컨디션을 함께 점검해요.',
    icon: 'paw-outline',
    verifiedLabel: '2026.08.27 확인',
    badges: [
      { label: '첫 여행', tone: 'orange' },
      { label: '동선 여유', tone: 'mint' },
    ],
  },
  {
    id: 'prep-jeju-entry',
    title: '제주도 동물 반입 규정',
    description: '개·고양이는 제주도 반입신고 대상이 아니라는 점을 행정 자료 기준으로 정리했어요.',
    icon: 'document-text-outline',
    verifiedLabel: '2026.08.27 확인',
    badges: [
      { label: '행정 자료', tone: 'green' },
      { label: '개·고양이', tone: 'mint' },
    ],
  },
];

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
