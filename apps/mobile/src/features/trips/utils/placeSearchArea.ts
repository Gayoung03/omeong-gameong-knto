import type { PlaceSearchArea } from '../api/placeSearchApi';
import type { Schedule, ScheduleItem } from '../types/trip';

/**
 * 일정 추가 화면이 어디를 기준으로 장소를 찾을지 정한다.
 *
 * **평균 좌표(중심점)를 쓰지 않는다.** 하루 일정이 넓게 퍼지면 중심점은
 * 아무 일정과도 가깝지 않은 곳으로 간다. 협재 → 애월 → 성산 숙소로 이어지는
 * 씨앗 데이터의 Day 1 은 중심점이 한라산 한복판이고, 가장 가까운 일정도 17km 밖이다.
 * 제주 여행은 숙소가 섬 반대편인 경우가 흔해서 이게 예외가 아니라 기본값이다.
 *
 * 그래서 **기준점은 그 날짜의 마지막 일정**이고, **반경은 그 날짜가 퍼진 폭에 맞춰** 늘린다.
 */

const EARTH_RADIUS_METERS = 6_371_000;

/** 일정이 하나뿐이거나 한곳에 몰려 있어도 이만큼은 본다. */
const MIN_RADIUS_METERS = 15_000;

/** 일정 폭 바깥으로 이만큼 더 본다. 루트 끝에서 조금 더 나가는 정도. */
const RADIUS_MARGIN_METERS = 15_000;

/** 제주 동서 폭이 약 73km 다. 그 이상은 사실상 '전체'라 늘릴 이유가 없다. */
const MAX_RADIUS_METERS = 100_000;

/** 숙소 근처. 차로 15~20분 거리. */
const STAY_RADIUS_METERS = 15_000;

function toRadians(degrees: number): number {
  return (degrees * Math.PI) / 180;
}

/** 두 좌표 사이 거리(미터). 하버사인 — 서버의 거리 계산과 같은 방식이다. */
function distanceMeters(
  from: { latitude: number; longitude: number },
  to: { latitude: number; longitude: number },
): number {
  const deltaLatitude = toRadians(to.latitude - from.latitude);
  const deltaLongitude = toRadians(to.longitude - from.longitude);

  const a =
    Math.sin(deltaLatitude / 2) ** 2 +
    Math.cos(toRadians(from.latitude)) *
      Math.cos(toRadians(to.latitude)) *
      Math.sin(deltaLongitude / 2) ** 2;

  return 2 * EARTH_RADIUS_METERS * Math.asin(Math.sqrt(a));
}

/** 좌표를 소수점 6자리에서 끊는다. 미터 단위 정밀도이고, 캐시 키가 부동소수 찌꺼기로 갈리지 않는다. */
function round(value: number): number {
  return Number(value.toFixed(6));
}

/**
 * 그 날짜의 검색 범위.
 *
 * 기준점은 **마지막 일정** — 사용자가 이어서 담을 위치다.
 * 반경은 그 기준점에서 가장 먼 일정까지의 거리 + 여유. 일정이 몰려 있으면 좁게,
 * 섬을 가로지르면 넓게 잡힌다.
 *
 * 일정이 하나도 없으면 기준점 자체가 없다(`null`). 그때는 전체 목록을 보여준다.
 */
export function toDaySearchArea(items: ScheduleItem[]): PlaceSearchArea | null {
  const anchor = items[items.length - 1]?.place;

  if (!anchor) {
    return null;
  }

  const spread = items.reduce(
    (farthest, item) => Math.max(farthest, distanceMeters(anchor, item.place)),
    0,
  );

  return {
    latitude: round(anchor.latitude),
    longitude: round(anchor.longitude),
    radius: Math.min(
      MAX_RADIUS_METERS,
      Math.round(Math.max(MIN_RADIUS_METERS, spread + RADIUS_MARGIN_METERS)),
    ),
  };
}

/**
 * 숙소 검색 범위.
 *
 * 여행 정보의 `accommodationSummary` 는 문장이라 좌표가 없다. 일정에 담긴
 * 숙소 분류 장소를 첫 번째로 찾아 쓴다. 없으면 `null` — '내 숙소' 탭이 비어 있게 둔다.
 */
export function toStaySearchArea(schedules: Schedule[]): PlaceSearchArea | null {
  for (const schedule of schedules) {
    const stay = schedule.items.find((item) => item.place.category === 'accommodation');

    if (stay) {
      return {
        latitude: round(stay.place.latitude),
        longitude: round(stay.place.longitude),
        radius: STAY_RADIUS_METERS,
      };
    }
  }

  return null;
}
