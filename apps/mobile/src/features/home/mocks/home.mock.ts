import type { EditorialStory, WeatherSummary } from '../types/home';

// TODO: 백엔드 날씨 API 연동 후 동일한 WeatherSummary 타입으로 교체합니다.
export const mockWeather: WeatherSummary = {
  greeting: '안녕, 보호자님!',
  location: '제주시',
  temperature: 24,
  condition: '구름 많음',
  humidity: 72,
  windSpeed: 4,
  tip: '바람이 많이 불어요. 산책할 때 옷을 챙겨주세요!',
};

// TODO: 관리자용 콘텐츠 API가 준비되면 EditorialStory[] 응답으로 교체합니다.
export const mockEditorialStories: EditorialStory[] = [
  {
    id: 'summer-jeju',
    category: '계절 여행',
    cardTitle: '반려동물과 갈 수 있는\n제주 여름 휴양지',
    title: '반려동물과 갈 수 있는 제주 여름 휴양지',
    summary: '시원한 바다와 숲길을 반려견과 안전하고 여유롭게 즐기는 방법을 소개해요.',
    heroImageUrl:
      'https://images.unsplash.com/photo-1508672019048-805c876b67e2?auto=format&fit=crop&w=900&q=80',
    publishedAt: '2026.08.12',
    readingMinutes: 5,
    author: '오멍가멍 에디터',
    sections: [
      {
        id: 'beach',
        heading: '아침 바다부터 천천히 시작해요',
        paragraphs: [
          '한낮의 뜨거운 모래는 반려견 발바닥에 부담이 될 수 있어요. 햇빛이 강해지기 전 이른 아침이나 해 질 무렵을 골라 산책해보세요.',
          '해변마다 반려동물 출입 기준이 다를 수 있으니 방문 전 최신 안내를 확인하고, 긴 리드줄과 충분한 물을 준비하는 것이 좋아요.',
        ],
        imageUrl:
          'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=900&q=80',
        imageCaption: '바람이 잔잔한 시간대의 제주 해변',
      },
      {
        id: 'forest',
        heading: '그늘이 있는 숲길도 함께 둘러보세요',
        paragraphs: [
          '바다 산책 뒤에는 나무 그늘이 이어지는 짧은 숲길을 추천해요. 아이의 호흡과 걸음 속도를 살피며 자주 쉬어주세요.',
        ],
      },
    ],
    tips: ['휴대용 물그릇과 생수를 챙겨주세요.', '뜨거운 지면은 손등으로 먼저 온도를 확인하세요.'],
    tags: ['여름', '해변', '숲길', '반려견 동반'],
  },
  {
    id: 'jeju-cafe',
    category: '날씨별 추천',
    cardTitle: '갑자기 만난 소나기,\n이런 카페는 어떠세요?',
    title: '갑자기 만난 소나기, 이런 카페는 어떠세요?',
    summary: '비 오는 제주에서도 반려견과 편안하게 머물 수 있는 카페를 고르는 기준을 정리했어요.',
    heroImageUrl:
      'https://images.unsplash.com/photo-1559925393-8be0ec4767c8?auto=format&fit=crop&w=900&q=80',
    publishedAt: '2026.08.09',
    readingMinutes: 4,
    author: '오멍가멍 에디터',
    sections: [
      {
        id: 'indoor-check',
        heading: '실내 동반 범위를 먼저 확인해요',
        paragraphs: [
          '반려동물 동반 가능 카페라도 실내 좌석은 제한되는 경우가 있어요. 이동장 사용 여부와 견종·무게 제한을 방문 전에 확인해주세요.',
        ],
        imageUrl:
          'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=900&q=80',
        imageCaption: '비 오는 날 잠시 쉬어가기 좋은 실내 공간',
      },
      {
        id: 'manners',
        heading: '모두가 편안한 카페 시간을 만들어요',
        paragraphs: [
          '젖은 털을 닦을 수건과 배변 봉투를 챙기고, 다른 손님과 반려동물의 거리를 충분히 확보하면 한결 편안하게 머물 수 있어요.',
        ],
      },
    ],
    tips: [
      '입장 전 매장에 실내 동반 가능 여부를 문의하세요.',
      '미끄럼 방지 매트나 작은 담요를 준비해보세요.',
    ],
    tags: ['비 오는 날', '카페', '실내 동반'],
  },
  {
    id: 'indoor-place',
    category: '실내 여행',
    cardTitle: '오늘 날씨에 맞는\n실내 장소 추천',
    title: '오늘 날씨에 맞는 제주 실내 장소 추천',
    summary: '비와 바람을 피해 반려동물과 함께 즐길 수 있는 실내 공간 선택법을 알려드려요.',
    heroImageUrl:
      'https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=900&q=80',
    publishedAt: '2026.08.05',
    readingMinutes: 6,
    author: '오멍가멍 에디터',
    sections: [
      {
        id: 'space',
        heading: '아이의 성향에 맞는 공간을 골라요',
        paragraphs: [
          '낯선 소리나 사람이 많은 곳을 어려워한다면 한적한 시간대와 넓은 동선을 갖춘 장소가 좋아요. 입장 규정과 이동장 사용 조건도 함께 살펴보세요.',
        ],
        imageUrl:
          'https://images.unsplash.com/photo-1560807707-8cc77767d783?auto=format&fit=crop&w=900&q=80',
        imageCaption: '실내에서도 아이가 쉴 자리를 먼저 마련해주세요',
      },
      {
        id: 'break',
        heading: '실내 일정 사이에도 휴식이 필요해요',
        paragraphs: [
          '실내에서는 냄새와 소리 같은 자극이 오래 이어질 수 있어요. 짧게 관람하고 조용한 곳에서 쉬는 시간을 일정에 넣어주세요.',
        ],
      },
    ],
    tips: ['이동장과 매너벨트 규정을 확인하세요.', '실내 온도에 맞춰 얇은 담요를 챙겨주세요.'],
    tags: ['실내', '우천 여행', '반려동물'],
  },
  {
    id: 'animal-hospital',
    category: '안전 가이드',
    cardTitle: '응급 상황 시\n갈 수 있는 동물병원',
    title: '제주 여행 중 응급 상황에 대비하는 방법',
    summary: '가까운 동물병원을 찾는 방법부터 진료 전에 준비할 정보까지 차근차근 확인해요.',
    heroImageUrl:
      'https://images.unsplash.com/photo-1517849845537-4d257902454a?auto=format&fit=crop&w=900&q=80',
    publishedAt: '2026.08.01',
    readingMinutes: 5,
    author: '오멍가멍 에디터',
    sections: [
      {
        id: 'prepare',
        heading: '숙소 근처 병원을 미리 저장해두세요',
        paragraphs: [
          '여행을 시작하기 전에 숙소와 주요 방문지 주변의 병원 위치, 운영 시간, 야간 진료 여부를 확인해두면 갑작스러운 상황에서도 빠르게 움직일 수 있어요.',
        ],
        imageUrl:
          'https://images.unsplash.com/photo-1628009368231-7bb7cfcb0def?auto=format&fit=crop&w=900&q=80',
        imageCaption: '방문 전 운영 시간과 진료 가능 여부를 확인하세요',
      },
      {
        id: 'call',
        heading: '이동 전 병원에 먼저 연락해요',
        paragraphs: [
          '증상과 발생 시점, 복용 중인 약을 정리해 전달하고 진료 가능 여부를 확인하세요. 평소 다니는 병원의 기록이나 처방전 사진도 도움이 됩니다.',
        ],
      },
    ],
    tips: [
      '예방접종 기록과 복용 약 정보를 휴대폰에 저장하세요.',
      '응급 상황에서는 병원 안내에 따라 안전하게 이동하세요.',
    ],
    tags: ['동물병원', '응급 상황', '여행 안전'],
  },
];
