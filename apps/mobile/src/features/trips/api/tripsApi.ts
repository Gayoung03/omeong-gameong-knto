import { MOCK_TRIPS } from '../mocks/trips.mock';
import type { Trip, TripListItem } from '../types/trip';

/**
 * 백엔드 /api/v1/trips 가 준비되기 전까지 Mock 데이터를 반환한다.
 * API 연동 시 이 파일의 구현만 apiClient 호출로 교체하고, Hook·화면은 수정하지 않는다.
 */
const MOCK_DELAY_MS = 300;

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), MOCK_DELAY_MS);
  });
}

function toListItem(trip: Trip): TripListItem {
  return {
    id: trip.id,
    title: trip.title,
    startDate: trip.startDate,
    endDate: trip.endDate,
    nights: trip.nights,
    days: trip.days,
    coverEmoji: trip.coverEmoji,
  };
}

/** 내 여행 목록 조회 */
export async function getTrips(): Promise<TripListItem[]> {
  return delay(MOCK_TRIPS.map(toListItem));
}

/** 여행 상세 조회 */
export async function getTrip(tripId: string): Promise<Trip> {
  const trip = MOCK_TRIPS.find((item) => item.id === tripId);

  if (!trip) {
    throw new Error(`여행을 찾을 수 없습니다. tripId: ${tripId}`);
  }

  return delay(trip);
}
