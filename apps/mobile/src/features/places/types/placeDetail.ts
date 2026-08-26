import type { PetPolicy } from '@/src/types/place';

/**
 * 장소 상세 화면이 보는 단일 모델.
 *
 * 예전에는 장소 데이터가 두 벌(장소 탐색 목데이터 · 내 여행 목데이터)이라
 * 어느 쪽에서 왔는지에 따라 채워지는 값이 달랐다. **이제 출처가 서버 하나다**
 * (`GET /places/{placeId}`). 그래서 `source` 와 `petFriendly` 를 지웠다.
 *
 * 서버가 안 주는 값은 여전히 `null` 이고, 화면은 `null` 인 항목을 그리지 않는다.
 * 상세 응답에는 거리가 없어(좌표 파라미터를 받지 않는다) 거리 칩도 함께 지웠다.
 */
export type PlaceDetail = {
  id: string;
  name: string;
  address: string;
  /** 화면에 그대로 보여줄 분류 문구 */
  categoryLabel: string;
  imageUrl: string | null;
  latitude: number;
  longitude: number;
  description: string | null;
  /** 서버가 정책 행이 없는 장소도 `unknown` 으로 내려주므로 항상 값이 있다. */
  petPolicy: PetPolicy;
  rating: number | null;
  reviewCount: number | null;
  savedCount: number | null;
  /**
   * 서버 `places.region` 원문.
   *
   * 목록의 `Place.region` 은 지역 칩 6종으로 옮기고 못 찾으면 `null` 이지만
   * (필터가 칩 이름으로 걸리기 때문), 상세는 필터가 없고 그냥 보여주기만 해서
   * 서버 값을 그대로 쓴다. 억지로 칩에 맞추면 정보만 사라진다.
   */
  region: string | null;
  environment: '실내' | '야외' | null;
  isReservable: boolean;
};
