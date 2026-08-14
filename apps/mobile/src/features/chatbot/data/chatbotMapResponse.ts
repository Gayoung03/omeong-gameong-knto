import { mockPlaces } from '@/src/features/places/data/placeMockData';
import type { Place } from '@/src/features/places/types/place';

const mapIntentKeywords = [
  '지도',
  '장소',
  '카페',
  '식당',
  '맛집',
  '숙소',
  '관광지',
  '병원',
  '산책',
  '갈 수',
  '어디',
  '주변',
  '여행지',
];

export function needsMapResponse(question: string) {
  return mapIntentKeywords.some((keyword) => question.includes(keyword));
}

export function getMapPlacesForQuestion(question: string): Place[] {
  const category = getRequestedCategory(question);
  const environment = question.includes('실내')
    ? '실내'
    : question.includes('산책')
      ? '야외'
      : null;

  const matchedPlaces = mockPlaces.filter((place) => {
    const matchesCategory = category ? place.category === category : true;
    const matchesEnvironment = environment ? place.environment === environment : true;
    return matchesCategory && matchesEnvironment && place.petFriendly;
  });

  return (
    matchedPlaces.length > 0 ? matchedPlaces : mockPlaces.filter((place) => place.petFriendly)
  ).slice(0, 3);
}

function getRequestedCategory(question: string): Place['category'] | null {
  if (question.includes('카페') || question.includes('식당') || question.includes('맛집')) {
    return '카페·식당';
  }
  if (question.includes('숙소')) return '숙소';
  if (question.includes('병원')) return '동물병원';
  if (question.includes('관광지')) return '관광지';
  return null;
}
