import type { PlaceCandidate, SchedulePlace } from '../types/trip';

/**
 * 후보 장소를 일정에 저장하는 형태로 바꾼다.
 * `regionLabel` 은 목록에 보여주기 위한 값이라 일정에는 담지 않는다.
 */
export function toSchedulePlace(candidate: PlaceCandidate): SchedulePlace {
  return {
    id: candidate.id,
    name: candidate.name,
    category: candidate.category,
    description: candidate.description,
    petPolicy: candidate.petPolicy,
    address: candidate.address,
    rating: candidate.rating,
    reviewCount: candidate.reviewCount,
    savedCount: candidate.savedCount,
    imageUrl: candidate.imageUrl,
    latitude: candidate.latitude,
    longitude: candidate.longitude,
    isReservable: candidate.isReservable,
  };
}
