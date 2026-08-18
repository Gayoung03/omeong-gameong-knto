import type { EditorialCard, WeatherSummary } from '../types/home';

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

export const mockEditorialCards: EditorialCard[] = [
  {
    id: 'summer-jeju',
    title: '반려동물과 갈 수 있는\n제주 여름 휴양지',
    imageUrl:
      'https://images.unsplash.com/photo-1508672019048-805c876b67e2?auto=format&fit=crop&w=900&q=80',
  },
  {
    id: 'jeju-cafe',
    title: '갑자기 만난 소나기,\n이런 카페는 어떠세요?',
    imageUrl:
      'https://images.unsplash.com/photo-1559925393-8be0ec4767c8?auto=format&fit=crop&w=900&q=80',
  },
  {
    id: 'indoor-place',
    title: '오늘 날씨에 맞는\n실내 장소 추천',
    imageUrl:
      'https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=900&q=80',
  },
  {
    id: 'animal-hospital',
    title: '응급 상황 시\n갈 수 있는 동물병원',
    imageUrl:
      'https://images.unsplash.com/photo-1517849845537-4d257902454a?auto=format&fit=crop&w=900&q=80',
  },
];
