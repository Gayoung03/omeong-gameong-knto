/**
 * 카카오 지도 JavaScript 앱 키.
 * `.env` 의 EXPO_PUBLIC_KAKAO_JS_KEY 에 넣는다. (`.env.example` 참고)
 *
 * 카카오 개발자 콘솔의 팀 앱 '오멍가멍'(ID 1533456) 키를 사용한다.
 * 제품 설정 > 카카오맵 > 사용 설정이 ON 이어야 하고, 무료 쿼터도 이 앱에 배정돼 있다.
 */
export const KAKAO_JS_KEY = process.env.EXPO_PUBLIC_KAKAO_JS_KEY ?? '';

/**
 * WebView 안에서 로컬 HTML 을 띄울 때 사용할 기준 주소.
 *
 * 실제로 이 주소에 접속하는 것은 아니다. HTML 은 앱이 직접 넘기고,
 * 이 값은 카카오 서버에 전달되는 출처(Referer)를 정하는 역할만 한다.
 *
 * 빈 문자열이면 기준 주소를 지정하지 않는다. 이때 카카오에는 출처가 전달되지 않는데,
 * 카카오는 출처 없는 요청을 허용하므로 개발 중에는 이 상태로도 지도가 동작한다.
 *
 * 배포 시 실제 도메인이 정해지면 그 주소를 여기에 넣고,
 * 개발자 콘솔의 **플랫폼 > Web > 사이트 도메인**에도 똑같이 등록한다.
 * (경로나 후행 슬래시는 넣으면 안 된다. 반영에 시간이 걸릴 수 있다.)
 */
export const KAKAO_MAP_BASE_URL = '';

/** 지도 초기 중심 (제주도) */
export const JEJU_CENTER = { latitude: 33.3846, longitude: 126.5535 };
